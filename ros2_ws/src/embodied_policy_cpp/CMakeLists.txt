cmake_minimum_required(VERSION 3.22)
project(embodied_policy_cpp)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
  set(CMAKE_CXX_STANDARD_REQUIRED ON)
endif()

find_package(ament_cmake REQUIRED)
find_package(embodied_core REQUIRED)

find_package(onnxruntime CONFIG REQUIRED)

add_library(${PROJECT_NAME} SHARED
  src/onnx_session.cpp
  src/rl_brain.cpp
  src/hybrid_brain.cpp
)
target_include_directories(${PROJECT_NAME} PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_compile_features(${PROJECT_NAME} PUBLIC cxx_std_17)
target_link_libraries(${PROJECT_NAME}
  PUBLIC
    embodied_core::embodied_core
    onnxruntime::onnxruntime
)

install(
  DIRECTORY include/
  DESTINATION include
)
install(
  TARGETS ${PROJECT_NAME}
  EXPORT export_${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

ament_export_targets(export_${PROJECT_NAME} HAS_LIBRARY_TARGET)
ament_export_include_directories(include)
ament_export_libraries(${PROJECT_NAME})
ament_export_dependencies(embodied_core)

if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)

  set(NAV_POLICY_ONNX "$ENV{NAV_POLICY_ONNX}")
  if(NAV_POLICY_ONNX STREQUAL "")
    set(NAV_POLICY_ONNX "${CMAKE_CURRENT_SOURCE_DIR}/test/fixtures/nav_policy.onnx")
  endif()

  ament_add_gtest(test_rl_brain_onnx
    test/test_rl_brain_onnx.cpp
  )
  target_link_libraries(test_rl_brain_onnx ${PROJECT_NAME})
  target_include_directories(test_rl_brain_onnx PRIVATE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/test>
  )
  target_compile_definitions(test_rl_brain_onnx PRIVATE
    NAV_POLICY_ONNX_PATH=\"${NAV_POLICY_ONNX}\"
  )
endif()

ament_package()
