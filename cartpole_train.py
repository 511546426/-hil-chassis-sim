"""CartPole 强化学习入门 —— PPO 训练与可视化测试。"""

import gymnasium as gym
from stable_baselines3 import PPO

env = gym.make('CartPole-v1')
model = PPO('MlpPolicy', env, verbose=1)
model.learn(total_timesteps=10000)
model.save('cartpole_ppo')

env = gym.make('CartPole-v1', render_mode='human')
obs, _ = env.reset()
total_reward = 0
for _ in range(1000):
    action, _ = model.predict(obs)
    obs, reward, terminated, truncated, _ = env.step(action)
    total_reward += reward
    if terminated or truncated:
        break

print(f'测试完成，得分: {total_reward}')
env.close()
