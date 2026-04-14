on run
	set projectRoot to "__PROJECT_ROOT__"
	set shellScript to projectRoot & "/scripts/launch_memo_sync.sh"
	do shell script "chmod +x " & quoted form of shellScript & "; " & quoted form of shellScript
end run
