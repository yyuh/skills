param(
  [string]$Title = "公众号存稿告警",
  [string]$Body = "存稿失败，请检查。",
  [int]$Timeout = 0
)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$shown = $false
try {
  # Windows 8+ Toast（需要 Start Menu 快捷方式注册 AUMID；失败则回落 MessageBox）
  $null = [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
  $tmpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
  $txt = $tmpl.GetElementsByTagName('text')
  $txt.Item(0).AppendChild($tmpl.CreateTextNode($Title)) | Out-Null
  $txt.Item(1).AppendChild($tmpl.CreateTextNode($Body)) | Out-Null
  $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("gzh-publish")
  $toast = [Windows.UI.Notifications.ToastNotification]::new($tmpl)
  $notifier.Show($toast)
  $shown = $true
  Start-Sleep -Seconds 1
} catch {
  $shown = $false
}
if (-not $shown) {
  # 兜底：始终可见的 MessageBox（阻塞直到用户点击确认）
  [System.Windows.Forms.MessageBox]::Show($Body, $Title, [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning)
}
