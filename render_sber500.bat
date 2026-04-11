@echo off
chcp 65001 >nul
set SRC=D:\Pavel\Рабочий стол\!!! АВТОМАТИЗАЦИЯ !!!\!!! Детектор Уязвимостей !!!\Результаты от LLM\VulnDetector__ИТ-иммунитет.mp4
set OUT=D:\Pavel\Рабочий стол\!!! АВТОМАТИЗАЦИЯ !!!\!!! Щелканогов Павел !!!\Shchelkanogov\Sber500_Demo_Final.mp4

echo === Rendering Sber500 Demo Video ===
echo Source: %SRC%
echo Output: %OUT%
echo.

ffmpeg -y -i "%SRC%" -t 300 -vf "split[main][blur];[blur]crop=220:40:iw-230:ih-50,boxblur=20:20[blurred];[main][blurred]overlay=W-230:H-50,drawtext=text='VulnDetector // Sber500':fontsize=18:fontcolor=white@0.8:x=w-250:y=h-40:fontfile='C\:/Windows/Fonts/arial.ttf'" -c:v libx264 -preset fast -crf 22 -c:a aac -b:a 128k "%OUT%"

echo.
echo === Done! Output: %OUT% ===
pause
