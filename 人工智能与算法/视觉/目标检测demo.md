## 2. 环境准备

### 前置条件

SDK 源码获取和基础编译环境配置统一参考 2.3-构建编译。完成 SDK 初始化后，回到本文继续执行“构建编译”。

后续命令默认在 K1 设备的 `spacemit_robot` SDK 根目录执行。

### 构建编译

系统缺少依赖时先安装：

```bash
sudo apt install python3-spacemit-ort opencv-spacemit spacemit-onnxruntime \
    eigen-spacemit openblas-spacemit libeigen3-dev libyaml-cpp-dev \
    python3-venv python3-numpy libtesseract5
```

在 SDK 根目录加载构建环境，选择 K1 target，然后编译视觉组件：

```bash
cd /root/spacemit_robot
source build/envsetup.sh
lunch k1-muse-pipro-ai-cubpet

cd components/model_zoo/vision
mm
```

SDK 集成构建会把 `yolov8`、`yolov5`、`yolov11`、`yolo12` 等示例程序安装到 `output/staging/bin`。

### 安装 Python 接口

运行 Python 示例前，先创建并激活虚拟环境：

```bash
cd /root/spacemit_robot/components/model_zoo/vision
if [ ! -d /root/.comm-env ]; then
    /usr/bin/python3 -m venv /root/.comm-env
fi
source /root/.comm-env/bin/activate
```

安装 Python 构建工具和运行依赖：

```bash
python3 -m pip install -U pybind11 build setuptools wheel
python3 -m pip install pyyaml
```

K1 当前厂商 OpenCV 需配合 NumPy 1.x 使用。将系统 Python 包目录和厂商 OpenCV 加入搜索路径，优先使用系统提供的 NumPy：

```bash
export PYTHONPATH="/usr/lib/python3/dist-packages:/opt/opencv-spacemit/lib/python3.12/dist-packages/cv2/python-3${PYTHONPATH:+:$PYTHONPATH}"
```

构建并安装 `spacemit_vision` wheel：

```bash
cmake -S . -B build \
    -DPython3_EXECUTABLE=/root/.comm-env/bin/python3
cmake --build build -j4

python3 -m pip install --force-reinstall --no-deps src/python/dist/*.whl

python3 -c \
'import cv2, numpy, yaml; from spacemit_vision import VisionServiceNative; print("ok")'
```

输出 `ok` 表示 Python 接口安装及导入检查成功。每次新开终端运行 Python 示例时，需重新激活虚拟环境并执行上述 `export PYTHONPATH` 命令。

模型权重默认存放路径为 `~/.cache/models/vision/yolov8/`、`~/.cache/models/vision/yolov5/`、`~/.cache/models/vision/yolov11/`、`~/.cache/models/vision/yolo12/`。运行示例前须执行对应模型的下载脚本；模型缺失时程序会报错 `Model file not found`。







## 2. 环境准备

### 前置条件

SDK 源码获取和基础编译环境配置统一参考 [2.3-构建编译](../../02-快速入门/2.3-构建编译.md)。完成 SDK 初始化后，回到本文继续执行“构建编译”。

后续命令默认在 K3 设备的 `spacemit_robot` SDK 根目录执行。

### 构建编译

系统缺少依赖时先安装：

```
sudo apt install python3-spacemit-ort opencv-spacemit \
    libeigen3-dev spacemit-onnxruntime libyaml-cpp-dev \
    python3-venv libogre1.12.10t64
```

在 SDK 根目录加载构建环境，选择 K3 target，然后编译视觉组件：

```
cd /root/spacemit_robot
source build/envsetup.sh
lunch k3-com260-omni-agent

cd components/model_zoo/vision
mm
```

SDK 集成构建会把 `yolov8`、`yolov5`、`yolov11`、`yolo12` 等示例程序安装到 `output/staging/bin`。

### 安装 Python 接口

运行 Python 示例前，先创建并激活虚拟环境：

```
cd /root/spacemit_robot/components/model_zoo/vision

if [ ! -d /root/.comm-env ]; then
    /usr/bin/python3 -m venv /root/.comm-env
fi
source /root/.comm-env/bin/activate
```

安装 Python 构建工具和运行依赖：

```
python3 -m pip install -U pybind11 build setuptools wheel
python3 -m pip install numpy pyyaml
```

厂商 OpenCV 位于系统目录，需要加入 Python 模块搜索路径：

```
export PYTHONPATH="/opt/opencv-spacemit/lib/python3.14/dist-packages/cv2/python-3${PYTHONPATH:+:$PYTHONPATH}"
```

构建并安装 `spacemit_vision` wheel：

```
cmake -S . -B build \
    -DPython3_EXECUTABLE=/root/.comm-env/bin/python3
cmake --build build -j4

python3 -m pip install --force-reinstall --no-deps \
    src/python/dist/*.whl

python3 -c \
'import cv2, numpy, yaml; from spacemit_vision import VisionServiceNative; print("ok")'
```

输出 `ok` 表示 Python 接口安装成功。

模型权重默认存放路径为 `~/.cache/models/vision/yolov8/`、`~/.cache/models/vision/yolov5/`、`~/.cache/models/vision/yolov11/`、`~/.cache/models/vision/yolo12/`。运行示例前须执行对应模型的下载脚本；模型缺失时程序会报错 `Model file not found`。