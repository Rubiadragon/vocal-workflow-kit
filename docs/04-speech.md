# 讲话：GPT-SoVITS训练与合成

[文档导航](INDEX.md) / 讲话

## 和RVC分开

GPT-SoVITS负责“文字 → 声音”；RVC负责“已有声音 → 目标音色”。
RVC的pth/index不能当作GPT-SoVITS的GPT/SoVITS权重使用。相同目标人物也需要分别准备相应工程和授权素材。

## 讲话音色训练流程

1. **选上游版本**：按官方说明选择版本，使用匹配的预训练模型和环境。不要在一个工程里混不同架构权重。
2. **收集净语音**：同一目标说话者，覆盖常见音素、语速和自然表达；避免背景人声、失真和过量去噪。
3. **分段与转写**：用上游工具切片、ASR辅助标注，逐条核对文字、语言和说话人。ASR错字会进入训练。
4. **准备训练数据**：按上游界面完成文本、语义/声学等准备步骤，检查日志和有效数量。
5. **微调SoVITS与GPT部分**：使用上游版本推荐配置，再根据显存与留出测试调整；不套用RVC的batch、采样率和epochs。
6. **留出验收**：未见过的短句、长句、问句、停顿、数字和目标语言。分别听音色、可懂度、韵律与稳定性。
7. **记录版本**：权重、基底版本、数据版本、配置、训练轮次、参考音频和参考文本；不要公开私人参考录音。

```powershell
python -m vocal_workflows train-plan --kind speech
```

本命令只列出准备步骤，不调用训练。训练参数和命令以当前上游WebUI为准；本项目不提供自动一键训练承诺。

## 本地讲话服务

先在上游工程配置自己的GPT与SoVITS权重，确认参考音频和文本，再按其说明启动API v2，通常使用本机9880端口。
不要把别人电脑的启动命令、模型路径或配置直接照搬。

编辑 config.local.json：

```json
{
  "speech": {
    "api_base": "http://127.0.0.1:9880",
    "allow_remote": false,
    "reference_audio": "datasets/reference.wav",
    "reference_text": "与参考录音逐字对应的内容。",
    "reference_language": "zh",
    "text_language": "zh"
  }
}
```

这里只展示speech段，不是可以覆盖整个配置文件的完整配置。

```powershell
python -m vocal_workflows doctor --speech --json
python -m vocal_workflows speak --text "这是一次新的本地语音测试。" --dry-run
python -m vocal_workflows speak --text "这是一次新的本地语音测试。"
```

适配器调用POST /tts，返回WAV后保存到workspace/speech。它不切换正在使用的模型，不启动或关闭服务。
API存在不代表音色选对；收到WAV也不代表发音和角色感合格，仍需试听。
参考路径由TTS服务所在电脑解释；默认适用于同一台电脑。远程API默认拒绝，显式开启前应理解文字和参考信息会传往对方。

参考：[GPT-SoVITS 官方项目](https://github.com/RVC-Boss/GPT-SoVITS)、[API v2](https://github.com/RVC-Boss/GPT-SoVITS/blob/main/api_v2.py)。
