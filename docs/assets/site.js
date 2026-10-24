document.getElementById('copy').addEventListener('click',async function(){
  const text=document.getElementById('commands').innerText;
  try{await navigator.clipboard.writeText(text);this.textContent='已复制';setTimeout(()=>this.textContent='复制',1800)}
  catch{this.textContent='请选中文本复制'}
});
document.getElementById('copy-ai').addEventListener('click',async function(){
  const prompt='项目地址：https://github.com/Rubiadragon/vocal-workflow-kit 。请先打开并阅读这个仓库，再帮我配置到电脑。先读取仓库中的 AGENTS.md、AI_HANDOFF.md、README.md 和 docs/compatibility.md。确认我需要讲话、训练准备、精唱还是快速翻唱，先诊断环境和运行测试，再列出缺失项。按我的授权配置本地依赖、音色和路径；不要上传文件、自动训练、关闭其他程序或改安全设置。修 bug 前备份，保留已有结果，分别报告计划、测试和真实推理是否通过。';
  const status=document.getElementById('ai-copy-status');
  try{await navigator.clipboard.writeText(prompt);status.textContent='已复制，已包含项目地址。直接发给你的 AI 即可。'}
  catch{status.textContent=prompt}
});
