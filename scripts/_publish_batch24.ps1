# batch24 串行存稿脚本
$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$root = "C:\Users\18480\Desktop\项目\skill\gzh-publish-公众号推送"
$out = "$root\outputs"
$logFile = "$out\batch24_publish_results.txt"

# 清空结果日志
"" | Out-File -FilePath $logFile -Encoding utf8

$articles = @(
    @{
        num = "01"
        html = "batch24_01_markitdown_新丑撞色(neo-brutalism).html"
        title = "PDF/Word/PPT一键转Markdown，微软这个开源工具省了我3小时"
        cover = "covers\batch24_01_cover.jpg"
        images = @("body_images\batch24_01_real1.jpg", "body_images\batch24_01_ai1.jpg", "body_images\batch24_01_real2.jpg")
    },
    @{
        num = "02"
        html = "batch24_02_hyperframes_包豪斯(bauhaus).html"
        title = "写HTML就能生成视频，HeyGen开源这个工具让剪辑师慌了"
        cover = "covers\batch24_02_cover.jpg"
        images = @("body_images\batch24_02_real1.jpg", "body_images\batch24_02_ai1.jpg", "body_images\batch24_02_real2.jpg")
    },
    @{
        num = "03"
        html = "batch24_03_i-have-adhd_红白(red-white).html"
        title = "AI回答又臭又长？这个技能让Claude Code一句话说清重点"
        cover = "covers\batch24_03_cover.jpg"
        images = @("body_images\batch24_03_ai1.jpg", "body_images\batch24_03_ai2.jpg", "body_images\batch24_03_ai3.jpg")
    },
    @{
        num = "04"
        html = "batch24_04_teamai-cli_新丑撞色(neo-brutalism).html"
        title = "腾讯开源的团队AI工具，让整个团队都变成AI原生玩家"
        cover = "covers\batch24_04_cover.jpg"
        images = @("body_images\batch24_04_ai1.jpg", "body_images\batch24_04_ai2.jpg", "body_images\batch24_04_ai3.jpg")
    },
    @{
        num = "05"
        html = "batch24_05_GPT6_Astra_包豪斯(bauhaus).html"
        title = "GPT-6能自己操作电脑，但你的工作流程该重做了"
        cover = "covers\batch24_05_cover.jpg"
        images = @("body_images\batch24_05_real1.jpg", "body_images\batch24_05_ai1.jpg", "body_images\batch24_05_real2.jpg")
    },
    @{
        num = "06"
        html = "batch24_06_AI解数学难题_红白(red-white).html"
        title = "AI解出百年数学难题，但90%团队方向错了"
        cover = "covers\batch24_06_cover.jpg"
        images = @("body_images\batch24_06_real1.jpg", "body_images\batch24_06_ai1.jpg", "body_images\batch24_06_real2.jpg")
    },
    @{
        num = "07"
        html = "batch24_07_DeepSeek_V4.1_Flash_新丑撞色(neo-brutalism).html"
        title = "DeepSeek又发新模型，但先别急着换"
        cover = "covers\batch24_07_cover.jpg"
        images = @("body_images\batch24_07_real1.jpg", "body_images\batch24_07_ai1.jpg", "body_images\batch24_07_real2.jpg")
    },
    @{
        num = "08"
        html = "batch24_08_外滩大会AI新经济_包豪斯(bauhaus).html"
        title = "AI烧钱烧不出增长，大佬说了句大实话"
        cover = "covers\batch24_08_cover.jpg"
        images = @("body_images\batch24_08_real1.jpg", "body_images\batch24_08_ai1.jpg", "body_images\batch24_08_real2.jpg")
    },
    @{
        num = "09"
        html = "batch24_09_AI时代复利思维_红白(red-white).html"
        title = "AI时代的复利思维：不是攒钱，是攒可复用的能力"
        cover = "covers\batch24_09_cover.jpg"
        images = @("body_images\batch24_09_ai1.jpg", "body_images\batch24_09_ai2.jpg", "body_images\batch24_09_ai3.jpg")
    },
    @{
        num = "10"
        html = "batch24_10_AI越聪明人越要笨功夫_日式(japanese-mag).html"
        title = "AI越聪明，人越要笨功夫：我用AI一年后最深刻的感悟"
        cover = "covers\batch24_10_cover.jpg"
        images = @("body_images\batch24_10_ai1.jpg", "body_images\batch24_10_ai2.jpg", "body_images\batch24_10_ai3.jpg")
    }
)

foreach ($a in $articles) {
    Write-Host "`n========== 开始存稿第 $($a.num) 篇: $($a.title) ==========" -ForegroundColor Cyan
    $resultLine = "[$($a.num)] $($a.title) => "

    # 杀掉Edge
    taskkill /F /IM msedge.exe 2>$null | Out-Null
    Start-Sleep -Seconds 2

    # 构建命令
    $imgArgs = ($a.images | ForEach-Object { "`"$out\$_`"" }) -join " "
    $cmd = "py -3.14 -B `"$root\scripts\publish_full_v2.py`" `"$out\$($a.html)`" --title `"$($a.title)`" --cover `"$out\$($a.cover)`" --body-images $imgArgs"

    Write-Host "执行命令: $cmd" -ForegroundColor Gray

    # 执行
    $output = cmd /c $cmd 2>&1
    $exitCode = $LASTEXITCODE

    # 提取appmsgid
    $appmsgid = ""
    foreach ($line in $output) {
        if ($line -match "appmsgid[=:：\s]+(\d+)") {
            $appmsgid = $Matches[1]
            break
        }
    }
    if (-not $appmsgid) {
        foreach ($line in $output) {
            if ($line -match "(\d{7,})") {
                $appmsgid = $Matches[1]
            }
        }
    }

    if ($exitCode -eq 0 -or $appmsgid) {
        $resultLine += "SUCCESS appmsgid=$appmsgid"
        Write-Host "✅ 存稿成功! appmsgid=$appmsgid" -ForegroundColor Green
    } else {
        $resultLine += "FAILED exit=$exitCode"
        Write-Host "❌ 存稿失败! exit=$exitCode" -ForegroundColor Red
        # 输出最后20行用于调试
        $output | Select-Object -Last 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor DarkGray }
    }

    # 写入结果日志
    $resultLine | Out-File -FilePath $logFile -Encoding utf8 -Append

    # 间隔
    Start-Sleep -Seconds 3
}

Write-Host "`n========== 全部存稿完成 ==========" -ForegroundColor Cyan
Write-Host "结果日志: $logFile"
Get-Content $logFile
