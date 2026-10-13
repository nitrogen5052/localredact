on run
	set theFiles to choose file with prompt "Choose file(s) to redact:" with multiple selections allowed
	processFiles(theFiles)
end run

on open theFiles
	processFiles(theFiles)
end open

on processFiles(theFiles)
	set scriptPath to POSIX path of (path to resource "redact.sh")
	set outputs to {}
	set failures to ""
	set total to count of theFiles
	set progress total steps to total
	set progress completed steps to 0
	repeat with i from 1 to total
		set f to item i of theFiles
		set fname to name of (info for f)
		set progress description to "Redacting " & fname & " (" & i & " of " & total & ")"
		set progress additional description to "Usually 15–30 seconds per file. Keep this window open."
		try
			set end of outputs to (do shell script quoted form of scriptPath & " " & quoted form of (POSIX path of f))
		on error errMsg
			set failures to failures & errMsg & return & return
		end try
		set progress completed steps to i
	end repeat
	if (count of outputs) > 0 then
		display notification ((count of outputs) as text) & " file(s) saved to Downloads" with title "redact-mac — done" sound name "Glass"
		do shell script "open -R " & quoted form of (item -1 of outputs)
		repeat with o in outputs
			do shell script "open -e " & quoted form of o
		end repeat
	end if
	if failures is not "" then display dialog failures with title "redact-mac" buttons {"OK"} default button 1 with icon caution
end processFiles
