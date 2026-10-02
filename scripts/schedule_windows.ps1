# Windows Task Scheduler registration script for KBM Tender Scout
# Schedules task "KBM_TenderScout_Daily" to run Sunday through Thursday at 06:00 AM Kuwait Time

$TaskName = "KBM_TenderScout_Daily"
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "src/run.py --portal all" -WorkingDirectory (Get-Location).Path
$Trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday, Monday, Tuesday, Wednesday, Thursday -At 06:00AM
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "KBM Daily Tender Monitoring Agent Run"
Write-Host "Scheduled task $TaskName successfully registered for Sunday-Thursday at 06:00 AM."
