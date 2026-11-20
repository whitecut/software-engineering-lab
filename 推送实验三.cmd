@echo off
set PATH=C:\study\rjgc\.tools\PortableGit\cmd;C:\study\rjgc\.tools\PortableGit\ucrt64\bin;%PATH%
cd /d C:\study\rjgc\lab3\实验3_241220081_刘子健
echo 正在推送 lab3 分支，若弹出 GitHub 登录窗口请完成授权...
git push -u origin lab3
git push origin lab3-final
pause
