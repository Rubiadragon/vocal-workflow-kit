# 兼容性与排错

## 支持契约

| 组件 | 本包预期 | 不应声称 |
|---|---|---|
| Python | 3.10+；各上游独立环境 | 一个环境能装下所有历史依赖 |
| RVC | `infer.modules.vc.modules.VC`、`vc_single`及legacy pipeline.get_f0 | 所有fork无需适配 |
| MSST | inference.py支持model_type/config_path/start_check_point/input_folder/store_dir/extract_instrumental/use_tta/device_ids/force_cpu | 新版pip API与旧整合包CLI完全相同 |
| 输出布局 | 单个输入对应唯一vocals.wav与instrumental.wav，可位于子目录 | 任意多说话人分离都能自动映射 |
| GPT-SoVITS | API v2 POST /tts、GET /openapi.json | 自动选择正确音色或兼容所有版本 |
| FFmpeg | 可执行程序、soxr、loudnorm分析、libmp3lame | 仅改文件后缀就是格式转换 |

MSST模型配置与权重必须配套，模型名称在示例中只是占位。不要把一个架构的配置传给另一个权重。
安装后先运行上游自己的最小推理，再运行本包短样。Windows是主要使用场景；macOS/Linux分支只有通用设计，发布前必须在目标系统实测。

## 分层验证

```powershell
python -m unittest discover -s tests -v
python -m vocal_workflows --config config.example.json doctor --json
```

示例配置缺少真实依赖时doctor返回退出码2是预期结果，不应把检查改成“无条件通过”。
测试生成临时合成WAV，不包含真实声音。音频测试需要audio依赖及FFmpeg，设置测试变量 `VW_TEST_FFMPEG` 指向实际可执行文件。
未配置时音频测试显示skip；必须如实区分skip和passed。

## 常见问题

- `ModuleNotFoundError`：确认命令调用的是哪个Python；嵌入式Python可能不把脚本目录放进sys.path。不要修改系统安全设置来修路径。
- CUDA内存不足：先查实际占用，不以总显存判断；显式选CPU或等待，不自动杀程序或换半精度。
- 分离完成但歌没做完：还需RVC、混音、编码、报告；不能只看分离manifest。
- 语音API根路径404：检查/openapi.json，不把根路径404等同于服务已停止。
- 有电音：对照干声、F0时间轴、输入音域、模型训练覆盖和索引强度；不能全归咎于一个旋钮。
- 双主唱：背景轨可能漏入主旋律；按实际角色核对，不仅看相关系数或音高阈值。
- 失败后重试：先检查原任务和产物；保留完成分离，避免复制旧歌脚本处理新歌。

上游更新可能改变参数、输出目录或依赖。AI修复应先补最小复现与契约测试，再改适配器，不改音色或输入来掩盖错误。
