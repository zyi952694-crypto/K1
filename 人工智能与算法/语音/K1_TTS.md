# 文本转语音（TTS）

## 1. 模块概述

TTS 组件提供统一的本地语音合成接口，负责把文本合成为 WAV/PCM 音频。组件位于 `components/model_zoo/tts`，提供 C++ API、文件合成 demo 和流式合成播放 demo，可用于机器人语音回复、固定提示音和离线语音生成。

支持的后端：

| 后端 | 语言 | 采样率 | 说明 |
| --- | --- | --- | --- |
| `matcha:zh` | 中文 | 22050 Hz | Matcha-TTS 中文模型。 |
| `matcha:en` | 英文 | 22050 Hz | Matcha-TTS 英文模型，依赖 `espeak-ng` 进行英文音素处理。 |
| `matcha:zh-en` | 中英混合 | 16000 Hz | Matcha-TTS 中英混合模型。 |
| `kokoro` | 英文 | 24000 Hz | `kokoro-v1.0-en` 模型，使用 `af_heart` 音色及 CPU 推理。 |

典型数据链路：

```text
输入文本 -> 分词/音素处理 -> TTS 后端 -> WAV/PCM -> 重采样 -> AudioPlayer 播放
```

主要目录：

| 路径 | 说明 |
| --- | --- |
| `components/model_zoo/tts/include/tts_service.h` | C++ 对外 API。 |
| `components/model_zoo/tts/src/backends/matcha/` | Matcha-TTS 后端。 |
| `components/model_zoo/tts/src/backends/kokoro/` | Kokoro 后端。 |
| `components/model_zoo/tts/examples/tts_file_demo.cpp` | C++ 文件合成示例。 |
| `components/model_zoo/tts/examples/tts_stream_demo.cpp` | 按句合成和队列播放的示例源码。 |

## 2. 环境准备

### 前置条件

先完成 K1 Robot SDK 源码获取和基础编译环境配置。本文命令均在 **K1 设备**上执行，SDK 根目录以 `/root/spacemit_robot` 为例。

TTS 依赖 ONNX Runtime / SpaceMIT EP、libsndfile、FFTW、libcurl 和 `espeak-ng`。音频播放还依赖 audio 组件、PortAudio、ALSA 和重采样库。后续示例默认使用已准备好这些依赖的 SDK 环境。

### 构建编译

语音组件使用 `target/k1-muse-pipro-ai-cubpet.json` 目标配置。在 K1 的 SDK 根目录加载构建环境：

```bash
cd /root/spacemit_robot
source build/envsetup.sh
lunch k1-muse-pipro-ai-cubpet
```

播放示例依赖 audio 组件。如 `output/staging/bin/audio_demo`、`output/staging/lib/libspacemit_audio.a` 或 `output/staging/lib/libaudio_resampler.a` 尚未生成，先在同一 shell 中编译 audio：

```bash
cd /root/spacemit_robot/components/multimedia/audio
mm
```

然后编译 TTS：

```bash
cd /root/spacemit_robot/components/model_zoo/tts
mm
```

构建产物安装到 `output/staging`，包括 `bin/tts_file_demo`、`bin/tts_stream_demo`、`include/tts/tts_service.h` 和 `lib/libtts.a`。

模型默认放在 `~/.cache/models/tts/` 下。Matcha 使用 `matcha-tts/` 子目录，英文 Kokoro 使用 `kokoro-tts/kokoro-v1.0-en/` 子目录。初始化时会检查模型并加载资源。中文 Matcha 使用 `cppjieba` 词典，中英混合模型使用 `cpp-pinyin` 词典；相关资源位于 `~/.cache/thirdparty/`。

## 3. 示例使用

本节命令在 **K1 的 `/root/spacemit_robot` 目录**执行。

### 3.1 文件合成

```bash
cd /root/spacemit_robot
./output/staging/bin/tts_file_demo \
    -p "今天学Python" -l matcha:zh-en --provider auto -o output.wav
```

程序输出引擎名称、采样率、音频时长、处理时间和 RTF，并保存 `output.wav`。`-l` 选择后端，`-o` 指定输出文件。

常用后端示例：

```bash
./output/staging/bin/tts_file_demo \
    -p "你好，欢迎使用语音合成。" -l matcha:zh --provider auto -o zh.wav

./output/staging/bin/tts_file_demo \
    -p "This is a longer English speech synthesis benchmark sentence for measuring real time factor on the platform." \
    -l matcha:en --provider auto -o en.wav

./output/staging/bin/tts_file_demo \
    -p "hello" -l kokoro --provider cpu -o kokoro_en.wav
```

### 3.2 自定义发音 lexicon

`tts_file_demo` 支持通过 `--lexicon` 指定中文词语或英文热词的读法。格式为 `word:phoneme[:locale]`，多个条目用逗号分隔。中文 phoneme 使用带声调拼音；`matcha:zh-en` 的英文热词可用 `locale=en` 交给 `espeak-ng` 处理。

```bash
./output/staging/bin/tts_file_demo \
    -p "你好，我是 SpaceMIT 的语音合成模型，很高兴为你服务。" \
    -l matcha:zh-en --provider auto \
    --lexicon "为你:wei4 ni3:zh,SpaceMIT:space meet:en" \
    -o lexicon_demo.wav
```

### 3.3 C++ 流式合成

查看音频设备列表，选择输出设备：

```bash
./output/staging/bin/tts_stream_demo -l
```

以下示例使用输出设备 `0`，以 48000 Hz、单声道播放。请根据实际声卡调整设备索引、采样率和声道数。

```bash
./output/staging/bin/tts_stream_demo \
    -p "你好世界。今天天气很好。" -e matcha:zh --provider auto \
    -o 0 --output-rate 48000 --channels 1
```

该示例模拟文本逐步输入，按句调用 `Call()` 合成，将音频放入播放队列，重采样后播放。`StreamingCall()` 回调接口的使用方法见 §4.2.3。

## 4. 应用开发

本章说明如何在 C++ 应用中集成 TTS 组件。完整接口以 `components/model_zoo/tts/include/tts_service.h` 为准。TTS 的 C++ 入口是 `SpacemiT::TtsEngine`。

### 4.1 接口说明

应用通过 `TtsEngine` 创建引擎、选择后端，并发起文件合成、PCM 合成或结果回调请求。

#### 4.1.1 常用数据结构

| 类型 | 说明 |
| --- | --- |
| `TtsConfig` | 引擎配置，通过 `Preset(name)` 创建预设；可指定 `backend`、`model_dir`、`provider` 和 `lexicon` 等字段。 |
| `BackendType` | 后端枚举，包括 `MATCHA_ZH`、`MATCHA_EN`、`MATCHA_ZH_EN` 和 `KOKORO`。 |
| `AudioFormat` | 音频格式，`PCM` 为原始音频数据，`WAV` 为音频文件格式。 |
| `PronunciationEntry` | 自定义发音条目，包含 `word`、`phoneme` 和 `locale` 字段。 |
| `TtsEngineResult` | 合成结果，提供音频数据、采样率、音频时长、处理时间、RTF 和成功状态等信息。 |
| `TtsResultCallback` | 结果回调基类，可覆写 `OnOpen()`、`OnEvent(result)`、`OnComplete()`、`OnError(message)` 和 `OnClose()`。 |

不同后端的输出采样率不同，接入播放器时应读取结果中的实际采样率。

#### 4.1.2 引擎初始化与预设

| 接口 | 说明 | 参数 | 返回值 |
| --- | --- | --- | --- |
| `TtsConfig::Preset(name)` | 创建后端预设配置。 | `matcha_zh`、`matcha_en`、`matcha_zh_en` 或 `kokoro`。 | `TtsConfig`。 |
| `TtsEngine(config)` | 根据配置创建并初始化引擎。 | `TtsConfig` 实例。 | 引擎实例。 |
| `IsInitialized()` | 检查初始化结果。 | 无。 | `bool`。 |
| `GetEngineName()` / `GetSampleRate()` / `GetNumSpeakers()` | 查询引擎名称、模型采样率和说话人数。 | 无。 | 各自类型。 |

应用应复用已初始化的引擎，避免每次合成重复加载模型和 warmup。

#### 4.1.3 阻塞合成

| 接口 | 说明 | 参数 | 返回值 |
| --- | --- | --- | --- |
| `Call(text, config=TtsConfig())` | 合成完整文本并返回音频结果。 | 输入文本和可选配置。 | `shared_ptr<TtsEngineResult>`。 |
| `CallToFile(text, file_path)` | 合成并保存 WAV。 | 输入文本和输出路径。 | `bool`。 |

调用 `Call()` 后应检查结果指针和 `IsSuccess()`。通过 `GetAudioInt16()` 或 `GetAudioFloat()` 获取 PCM，通过 `GetSampleRate()` 获取采样率。`GetDurationMs()`、`GetProcessingTimeMs()` 和 `GetRTF()` 分别返回音频时长、处理时间和实时率。

#### 4.1.4 流式合成

| 接口 | 说明 | 参数 | 返回值 |
| --- | --- | --- | --- |
| `StreamingCall(text, callback, config=TtsConfig())` | 同步合成完整文本，成功后回调一次音频结果。 | 输入文本、`shared_ptr<TtsResultCallback>` 和可选配置。 | 无，结果通过回调返回。 |

成功调用的回调顺序为 `OnOpen → OnEvent → OnComplete → OnClose`。回调在 `StreamingCall()` 调用过程中同步发生，当前接口不提供逐句增量推理。

#### 4.1.5 运行时配置

| 接口 | 说明 | 参数 | 返回值 |
| --- | --- | --- | --- |
| `UpdateLexicon(entries)` | 更新自定义发音词典，影响后续合成请求。 | `vector<PronunciationEntry>`。 | 无。 |

### 4.2 C++ 调用示例

以下示例默认已完成 §2 构建。TTS 头文件为 `output/staging/include/tts/tts_service.h`，静态库为 `output/staging/lib/libtts.a`。

将示例保存为应用目录中的 `main.cpp`，并创建以下 `CMakeLists.txt`：

```cmake
cmake_minimum_required(VERSION 3.16)
project(k1_tts_example LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(SDK_ROOT "/root/spacemit_robot" CACHE PATH "Robot SDK root")
set(STAGING_DIR "${SDK_ROOT}/output/staging")

add_executable(k1_tts_example main.cpp)
target_include_directories(k1_tts_example PRIVATE
    "${STAGING_DIR}/include/tts")
target_link_libraries(k1_tts_example PRIVATE
    "${STAGING_DIR}/lib/libtts.a"
    /usr/lib/libonnxruntime.so
    /usr/lib/libspacemit_ep.so
    fftw3 fftw3f curl
    "${STAGING_DIR}/lib/libkaldifst_core.a"
    "${STAGING_DIR}/lib/libkaldifst_fst.a"
    m pthread)
```

在 **K1 的应用目录**编译并运行：

```bash
cmake -S . -B build
cmake --build build -j4
./build/k1_tts_example
```

包依赖可在当前 SDK 组件的 `package.xml` 中声明 `<depend>tts</depend>`。

§4.2.2 和 §4.2.3 使用音频播放及重采样，需在上述 CMake 文件末尾追加：

```cmake
set(TTS_BUILD_DIR "${SDK_ROOT}/output/build/cmake/pkgs/components_model_zoo_tts")
target_include_directories(k1_tts_example PRIVATE "${STAGING_DIR}/include")
target_link_libraries(k1_tts_example PRIVATE
    "${STAGING_DIR}/lib/libspacemit_audio.a"
    "${STAGING_DIR}/lib/libaudio_resampler.a"
    "${TTS_BUILD_DIR}/_deps/portaudio-build/libportaudio.a"
    samplerate asound m pthread)
```

#### 4.2.1 一次性合成存 WAV

适用场景：离线合成、固定提示音生成。

调用步骤：

1. 用 `TtsConfig::Preset("matcha_zh")` 创建中文预设。
2. 构造 `TtsEngine` 并通过 `IsInitialized()` 检查。
3. 调用 `CallToFile(text, path)` 保存 WAV。

```cpp
#include <iostream>
#include "tts_service.h"

int main() {
    auto config = SpacemiT::TtsConfig::Preset("matcha_zh");
    SpacemiT::TtsEngine engine(config);
    if (!engine.IsInitialized()) {
        std::cerr << "TTS 初始化失败\n";
        return 1;
    }
    if (!engine.CallToFile("你好，欢迎使用语音合成。", "hello.wav")) {
        std::cerr << "TTS 合成失败\n";
        return 1;
    }
    return 0;
}
```

包含命令行参数解析的完整示例见 `components/model_zoo/tts/examples/tts_file_demo.cpp`。

#### 4.2.2 PCM 内存合成 + 直送播放器

适用场景：合成结果不落盘，直接送 `SpacemitAudio::AudioPlayer` 播放。

调用步骤：

1. 调用 `Call(text)` 获取合成结果。
2. 用 `GetAudioInt16()` 和 `GetSampleRate()` 获取 PCM16 样本及采样率。
3. 将 PCM 重采样为播放设备支持的采样率，再写入播放器。

以下示例使用输出设备 `0`，以 48000 Hz、单声道播放。设备索引应根据实际声卡选择。

```cpp
#include <algorithm>
#include <cstdint>
#include <vector>

#include "tts_service.h"
#include "audio_base.hpp"
#include "audio_resampler.hpp"

bool PlayPcm(const std::vector<int16_t>& pcm, int sample_rate) {
    const int output_rate = 48000;
    std::vector<float> input(pcm.size());
    for (size_t i = 0; i < pcm.size(); ++i) {
        input[i] = static_cast<float>(pcm[i]) / 32768.0f;
    }

    Resampler::Config config;
    config.input_sample_rate = sample_rate;
    config.output_sample_rate = output_rate;
    config.channels = 1;
    config.method = ResampleMethod::SRC_SINC_MEDIUM_QUALITY;
    Resampler resampler(config);
    if (!resampler.initialize()) return false;

    auto output = resampler.process(input);
    std::vector<int16_t> output_pcm(output.size());
    for (size_t i = 0; i < output.size(); ++i) {
        float sample = std::clamp(output[i], -1.0f, 1.0f);
        output_pcm[i] = static_cast<int16_t>(
            sample * (sample >= 0.0f ? 32767.0f : 32768.0f));
    }

    SpacemitAudio::AudioPlayer player(0);
    if (!player.Start(output_rate, 1)) return false;
    bool ok = player.Write(
        reinterpret_cast<const uint8_t*>(output_pcm.data()),
        output_pcm.size() * sizeof(int16_t));
    player.Stop();
    player.Close();
    return ok;
}

int main() {
    SpacemiT::TtsEngine engine(SpacemiT::TtsConfig::Preset("matcha_zh"));
    if (!engine.IsInitialized()) return 1;
    auto result = engine.Call("你好，这是 PCM 内存合成测试。");
    if (!result || !result->IsSuccess()) return 1;
    return PlayPcm(result->GetAudioInt16(), result->GetSampleRate()) ? 0 : 1;
}
```

#### 4.2.3 流式合成边播

`StreamingCall()` 当前在整段合成完成后返回一次结果回调。以下示例演示通过回调接收 PCM 并播放；它不会在单次合成过程中逐块输出音频。

保留 §4.2.2 中的头文件和 `PlayPcm()` 函数，将 `main()` 替换为以下代码，并补充列出的头文件：

```cpp
#include <iostream>
#include <memory>

class PlaybackCallback : public SpacemiT::TtsResultCallback {
public:
    void OnEvent(std::shared_ptr<SpacemiT::TtsEngineResult> result) override {
        if (!result || !result->IsSuccess()) return;
        success = PlayPcm(result->GetAudioInt16(), result->GetSampleRate());
    }

    void OnError(const std::string& message) override {
        std::cerr << message << std::endl;
        success = false;
    }

    bool success = false;
};

int main() {
    SpacemiT::TtsEngine engine(SpacemiT::TtsConfig::Preset("matcha_zh"));
    if (!engine.IsInitialized()) return 1;
    auto callback = std::make_shared<PlaybackCallback>();
    engine.StreamingCall("你好世界。今天天气很好。", callback);
    return callback->success ? 0 : 1;
}
```

#### 4.2.4 双向流（边输入文本边合成）

适用场景：上游持续产文本（典型如 LLM 流式输出），希望文本一边到达就一边触发合成，整体延迟最小化。

调用步骤：

1. 实现 `TtsResultCallback`，处理 chunk（参考 §4.2.3）。
2. 调用 `StartDuplexStream(callback)` 取得 `DuplexStream`。
3. 上游每收到一段文本就 `stream->SendText(piece)`；上游结束时调 `stream->Complete()`，等待 `OnComplete`。

```
auto engine = std::make_shared<SpacemiT::TtsEngine>(
    SpacemiT::TtsConfig::Preset("matcha_zh_en"));
auto cb = std::make_shared<PlaybackCallback>();

auto stream = engine->StartDuplexStream(cb);
stream->SendText("你好");
stream->SendText("世界，");
stream->SendText("现在开始流式合成。");
stream->Complete();   // 通知文本流结束
// 主线程继续从 cb->chunks_ 取数据播放，与 §4.2.3 相同
```

当前版本暂不支持双向流合成，`StartDuplexStream()` 返回空句柄，因此上述双向流示例无法真正实现。

#### 4.2.5 自定义发音 lexicon

适用场景：指定中文多音字、产品名称或英文热词的读法。

调用步骤：

1. 准备 `vector<PronunciationEntry>`，每条包含 `word`、`phoneme` 和 `locale`。
2. 调用 `UpdateLexicon(entries)` 更新词典。
3. 调用 `Call()` 或 `CallToFile()` 合成文本。

```cpp
#include <vector>
#include "tts_service.h"

int main() {
    SpacemiT::TtsEngine engine(SpacemiT::TtsConfig::Preset("matcha_zh_en"));
    if (!engine.IsInitialized()) return 1;

    std::vector<SpacemiT::PronunciationEntry> entries = {
        {"为你", "wei4 ni3", "zh"},
        {"SpaceMIT", "space meet", "en"},
    };
    engine.UpdateLexicon(entries);

    return engine.CallToFile(
        "你好，我是 SpaceMIT 的语音合成模型，很高兴为你服务。",
        "lexicon_demo.wav") ? 0 : 1;
}
```

`locale="zh"` 时，phoneme 为用空格分隔的带声调拼音；`matcha:zh-en` 使用 `locale="en"` 时，phoneme 可填写英文单词或短语，由 `espeak-ng` 处理发音。

### 4.3 Python 示例

Python 包名为 `spacemit_tts`，安装方式见 §2 中 wheel 安装步骤。导入后直接使用：

```
import spacemit_tts
```

#### 4.3.1 文件合成

```
import spacemit_tts

config = spacemit_tts.Config.preset("matcha_zh")
config.speech_rate = 1.0
config.volume = 80

with spacemit_tts.Engine(config) as engine:
    result = engine.synthesize("你好，欢迎使用语音合成。")
    print(f"采样率 {result.sample_rate} Hz, "
          f"时长 {result.duration_ms} ms, RTF {result.rtf:.3f}")
    result.save("hello.wav")
```

也可以用模块级快捷函数一句话存盘：

```
import spacemit_tts
spacemit_tts.synthesize_to_file("你好世界", "output.wav")
```

#### 4.3.2 流式合成

继承 `TtsCallback` 实现自定义回调，结合 `synthesize_streaming(text, callback)` 触发流式合成：

```
import numpy as np
import spacemit_tts

class CollectCallback(spacemit_tts.TtsCallback):
    def __init__(self):
        super().__init__()
        self.chunks = []
        self.sample_rate = 0

    def on_event(self, result):
        if result.is_success and not bool(result) is False:
            self.chunks.append(np.array(result.get_audio_int16(),
                                         dtype=np.int16))
            self.sample_rate = result.get_sample_rate()

    def on_error(self, message: str):
        print(f"[TTS] {message}")

cb = CollectCallback()
engine = spacemit_tts.Engine(spacemit_tts.Config.preset("matcha_zh"))
engine.synthesize_streaming("你好世界。今天天气很好。", cb)

audio = np.concatenate(cb.chunks) if cb.chunks else np.empty(0, dtype=np.int16)
print(f"共 {audio.size} 采样点，{cb.sample_rate} Hz")
```

也可直接复用包内置回调（`PrintCallback` / `SaveCallback` / `CollectCallback`），无需自己继承 ABC。完整流式 demo 见 `components/model_zoo/tts/python/examples/tts_stream_demo.py`。

#### 4.3.3 C++ ↔ Python 接口对照

| C++（`SpacemiT::`）                                   | Python（`spacemit_tts.`）                                    | 备注                                                         |
| ----------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| `TtsConfig` + `Preset(name)`                          | `Config(backend, model_dir)` 或 `Config.preset(name)`        | Python 字段通过属性 setter（`speech_rate` / `volume` / `speaker_id` / `sample_rate` / `pitch`）或链式 `with_speed/with_speaker/with_volume`。 |
| `TtsEngine(config)` + `IsInitialized()`               | `Engine(config)` 或 `with Engine(config) as engine`          | Python 构造时直接初始化，无需显式 `initialize()`；`engine.is_initialized` 查询状态。 |
| `Call(text)`                                          | `Engine.synthesize(text) → Result` 或 `synthesize(text)` 模块级快捷函数 |                                                              |
| `CallToFile(text, path)`                              | `Engine.synthesize_to_file(text, path) → bool` 或 `synthesize_to_file(text, path)` |                                                              |
| `StreamingCall(text, callback)`                       | `Engine.synthesize_streaming(text, callback)`                | callback 需为 `TtsCallback` 子类实例。                       |
| `StartDuplexStream(callback)`                         | 当前 Python 包**未暴露**                                     | 双向流场景请使用 C++ API。                                   |
| `TtsResultCallback`                                   | `TtsCallback`（ABC）/ `PrintCallback` / `SaveCallback` / `CollectCallback` | 后三者为内置便捷实现。                                       |
| `SetSpeed/SetSpeaker/SetVolume/UpdateLexicon`         | `engine.set_speed(speed)` / `set_speaker(id)` / `set_volume(vol)` / `update_lexicon(entries)` | `entries` 接受 dict 列表（`{"word": ..., "phoneme": ..., "locale": ...}`）或 `PronunciationEntry` 实例。 |
| `TtsEngineResult::GetAudioFloat/Int16/Data` 等 getter | `result.audio_float` / `audio_int16` / `audio_bytes` / `sample_rate` / `duration_ms` / `rtf` 属性 | Python 侧用属性而非方法；`result.save(path)` 等价 `SaveToFile`。 |

更多 Python 示例（含 Kokoro 多音色、双语切换）见 `components/model_zoo/tts/python/examples/`。

## 5. 调试指南

调试 TTS 时先确认后端、文本处理和播放链路：

- 先使用 `tts_file_demo` 确认文本能合成为 WAV，再检查音频播放。
- 英文或中英混合文本应确认 `espeak-ng`、lexicon 和词典资源是否可用。
- 播放异常时检查模型输出采样率、播放采样率和输出设备索引，按设备要求重采样。
- 性能评估以 warmup 后的合成 RTF 为准，模型加载和 warmup 耗时单独计算。

## 6. 常见问题

| 现象 | 可能原因 | 处理 |
| --- | --- | --- |
| 首次合成明显慢 | 模型加载和 warmup 开销。 | 应用启动时初始化引擎，后续请求复用同一实例。 |
| 英文发音异常 | `espeak-ng` 或词典资源缺失，热词读法未配置。 | 检查英文处理依赖，按需用 `--lexicon` 指定读法。 |
| 播放速度或音调异常 | 播放采样率与 PCM 采样率不一致。 | 读取结果采样率，使用 `Resampler` 转换后播放。 |
| Kokoro 合成耗时较长 | 英文模型使用 CPU 推理。 | 复用引擎，并根据附录的 RTF 评估应用响应时间。 |

## 附录：K1 实测数据

以下数据基于 K1-muse-pipro-ai-cubpet、Bianbu 2.3.5 和 `spacemit-onnxruntime 2.0.3-bpo1`。每项在同一进程内合成 3 次，取 RTF 中位数对应的音频时长和处理时间；模型下载、引擎初始化、warmup 和 WAV 文件保存不计入处理时间。

`matcha:zh` / `matcha:en` 使用 `--provider auto`，由 SpaceMIT EP 运行声学模型、CPU 运行 vocoder；`matcha:zh-en` 使用 `--provider auto`，声学模型和 vocoder 均在 CPU 上运行。英文 Kokoro 使用 `--provider cpu`，模型为 `kokoro-v1.0-en`，音色为 `af_heart`。

| 后端 | `-l` 参数 | 测试文本 | 音频时长 | 处理时间 | RTF |
| --- | --- | --- | --- | --- | --- |
| MATCHA_ZH | `matcha:zh` | 这是一个语音合成测试 | 2635 ms | 1206 ms | 0.457685 |
| MATCHA_EN | `matcha:en` | This is a longer English speech synthesis benchmark sentence for measuring real time factor on the platform. | 7151 ms | 3188 ms | 0.445812 |
| MATCHA_ZH_EN | `matcha:zh-en` | 今天学Python | 1920 ms | 1514 ms | 0.788542 |
| KOKORO_EN | `kokoro` | hello | 1400 ms | 16562 ms | 11.83 |

RTF 为合成处理时间与音频时长之比；RTF 小于 1 表示合成速度快于音频播放速度。

测试命令在 **K1 的 `/root/spacemit_robot` 目录**执行。将 `<text>` 和 `<engine>` 替换为表中对应内容；`<provider>` 对 Matcha 填写 `auto`，对 Kokoro 填写 `cpu`：

```bash
./output/staging/bin/tts_file_demo \
    -p "<text>" -l <engine> --provider <provider> --repeat 3 -o output.wav
```
