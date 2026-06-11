"""SB3 PPO → ONNX 导出与数值对齐验证（P3-M2）。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch as th
from stable_baselines3 import PPO


def _resolve_model_path(path: Path) -> Path:
    if path.suffix == '.zip':
        return path
    candidate = path.with_suffix('.zip')
    if candidate.is_file():
        return candidate
    return path


class NavActorOnnx(th.nn.Module):
    """SB3 ActorCriticPolicy 的确定性 actor（含 [-1,1] clip）。"""

    def __init__(self, policy) -> None:
        super().__init__()
        self.policy = policy

    def forward(self, obs: th.Tensor) -> th.Tensor:
        features = self.policy.extract_features(obs)
        latent_pi = self.policy.mlp_extractor.forward_actor(features)
        actions = self.policy.action_net(latent_pi)
        return th.clamp(actions, -1.0, 1.0)


def export_sb3_to_onnx(model_path: Path, output_onnx: Path) -> None:
    model = PPO.load(str(model_path), device='cpu')
    actor = NavActorOnnx(model.policy).eval()
    dummy = th.zeros(1, 8, dtype=th.float32)
    output_onnx.parent.mkdir(parents=True, exist_ok=True)
    th.onnx.export(
        actor,
        dummy,
        str(output_onnx),
        input_names=['obs'],
        output_names=['action'],
        dynamic_axes={'obs': {0: 'batch'}, 'action': {0: 'batch'}},
        opset_version=17,
    )
    import onnx

    model = onnx.load(str(output_onnx), load_external_data=True)
    onnx.save_model(model, str(output_onnx), save_as_external_data=False)
    data_sidecar = output_onnx.with_suffix('.onnx.data')
    if data_sidecar.is_file():
        data_sidecar.unlink()


def reference_test_vectors() -> list[np.ndarray]:
    rng = np.random.default_rng(42)
    return [
        np.zeros((1, 8), dtype=np.float32),
        np.array([[0.1, 0.2, 0.05, 0.3, -0.1, 0.4, 0.5, 0.2]], dtype=np.float32),
        rng.standard_normal((1, 8)).astype(np.float32),
        np.array([[0.5, -0.3, 0.25, -0.8, 0.6, 0.15, -0.4, 0.1]], dtype=np.float32),
    ]


def verify_python_alignment(model_path: Path, onnx_path: Path) -> float:
    model = PPO.load(str(model_path), device='cpu')
    session = ort.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
    max_err = 0.0
    for obs in reference_test_vectors():
        ort_out = session.run(None, {'obs': obs})[0]
        sb3_out, _ = model.predict(obs, deterministic=True)
        max_err = max(max_err, float(np.max(np.abs(ort_out - sb3_out))))
    return max_err


def write_test_vectors_header(
    model_path: Path,
    onnx_path: Path,
    output_hpp: Path,
) -> None:
    model = PPO.load(str(model_path), device='cpu')
    session = ort.InferenceSession(str(onnx_path), providers=['CPUExecutionProvider'])
    cases: list[dict[str, list[float]]] = []
    for obs in reference_test_vectors():
        expected = session.run(None, {'obs': obs})[0][0].tolist()
        cases.append({'obs': obs[0].tolist(), 'action': expected})

    lines = [
        '#pragma once',
        '',
        '#include <array>',
        '#include <cstddef>',
        '',
        'namespace embodied_policy_cpp {',
        '',
        'struct OnnxTestVector {',
        '  std::array<float, 8> obs{};',
        '  std::array<float, 2> action{};',
        '};',
        '',
        'inline constexpr std::array<OnnxTestVector, '
        f'{len(cases)}> kNavPolicyTestVectors = {{',
    ]
    for case in cases:
        obs = ', '.join(f'{v:.8f}f' for v in case['obs'])
        act = ', '.join(f'{v:.8f}f' for v in case['action'])
        lines.extend([
            '  OnnxTestVector{',
            f'    {{{obs}}},',
            f'    {{{act}}},',
            '  },',
        ])
    lines.extend([
        '};',
        '',
        '}  // namespace embodied_policy_cpp',
        '',
    ])
    output_hpp.parent.mkdir(parents=True, exist_ok=True)
    output_hpp.write_text('\n'.join(lines), encoding='utf-8')

    sidecar = output_hpp.with_suffix('.json')
    sidecar.write_text(json.dumps(cases, indent=2), encoding='utf-8')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Export SB3 nav policy to ONNX (P3-M2)')
    parser.add_argument('model', type=Path, help='Path to SB3 .zip model')
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output .onnx path (default: same dir as model, nav_policy.onnx)',
    )
    parser.add_argument(
        '--test-vectors-hpp',
        type=Path,
        default=None,
        help='Generate C++ test vectors header',
    )
    parser.add_argument('--verify', action='store_true', help='Verify SB3 vs ORT alignment')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    model_path = _resolve_model_path(args.model)
    if not model_path.is_file():
        print(f'ERROR: model not found: {model_path}', file=sys.stderr)
        return 1

    output_onnx = args.output
    if output_onnx is None:
        output_onnx = model_path.parent / 'nav_policy.onnx'
    elif output_onnx.suffix != '.onnx':
        output_onnx = output_onnx.with_suffix('.onnx')

    export_sb3_to_onnx(model_path, output_onnx)
    print(f'Exported: {output_onnx}')

    if args.test_vectors_hpp is not None:
        write_test_vectors_header(model_path, output_onnx, args.test_vectors_hpp)
        print(f'Test vectors: {args.test_vectors_hpp}')

    if args.verify:
        max_err = verify_python_alignment(model_path, output_onnx)
        print(f'Python SB3 vs ORT max error: {max_err:.2e}')
        if max_err >= 1e-4:
            print('FAIL: alignment error >= 1e-4', file=sys.stderr)
            return 1
        print('PASS: Python alignment')

    return 0


if __name__ == '__main__':
    sys.exit(main())
