# 精唱：只换主唱，保留原编排

[文档导航](INDEX.md) / 精唱

## 先确认声音的角色

“主唱”是音乐中的功能，不是性别或音高范围。主歌里的说唱可能就是主唱；客串说唱可能应当保留。
副歌口号也可能由主唱自己演唱。不要把所有男性、低于某个Hz、或所有“哟哟”直接排除。

分离模型输出的 lead / backing 是候选轨。对唱、客串与交叠位置必须核对：

- 应转换的歌词是否完整？字头、尾音、长音是否损伤？
- 应保留的客串是否还混在主唱轨里？
- 背景轨是否残留明显原主唱主旋律？混回后会不会出现双主唱？

无法分清时先交代表性短样给使用者确认，不做虚假的“已经全分开”结论。

## 默认链路

1. FFmpeg 解码成44.1k双声道浮点。
2. MSST 第一阶段分全人声与乐器，第二阶段分候选主唱与背景。
3. 分离参数 overlap=8、batch=1、TTA。模型配置必须与各自权重配套。
4. 仅指定主唱单声道送入 RVC；原背景与乐器不送入换声模型。
5. 精唱适配器在16k输入上提取100Hz RMVPE轨，保存并冻结；需匹配legacy RVC API。
6. 保留原调作为起点。移调依据音域与编排决定，不能所有男转女都固定升12半音。
7. 转换主唱应用活动掩码与静态响度增益；原乐器＋背景等增益相加，整体匹配响度。
8. 静态混音与真峰值检查，生成单独整曲MP3；中间音轨和报告留在独立运行目录。

初始 profile：index=0.3、protect=0.33、rms_mix_rate=1、原调、FP32。它是公开示例，不是任何特定人物音色的最佳参数。
protect在常见RVC接口中0.5表示关闭该保护；不是越大保护越强。rms_mix_rate=1偏向转换输出的包络，低值更贴输入包络；以实际fork实现为准。

```powershell
python -m vocal_workflows fine --source "input/song.wav" --dry-run
python -m vocal_workflows fine --source "input/song.wav" --roles-confirmed
```

`--roles-confirmed` 是操作者的确认，不是工具通过算法识别了角色。

## 复用已有分离

```powershell
python -m vocal_workflows fine --source "input/song.wav" --reuse "workspace/runs/previous/manifest.json" --roles-confirmed
```

必须同源、同模式、已完成，且音轨哈希一致。新输出使用新目录，不覆盖旧成品。
本版没有单独开放“只重混音”CLI；已有转换结果可由AI根据 `vocal_workflows/audio.py` 的 `mix` 函数在新目录调用，并对输入先后做哈希核验。
不要为了混回和声而重跑分离或换声。后续可把重混音功能扩成独立子命令并加测试。

## 成品验收

报告和最终文件都存在，状态completed，输入哈希未变，时长对齐、样本有限、没有削波、真峰值达标。
背景保留表示原背景轨参与混音，不意味着所有客串都分到了该轨；听审仍然独立。
CLI不发送QQ、不上传、不关闭其他应用。完成文件位于 workspace/finished，工作音轨在 workspace/runs。
