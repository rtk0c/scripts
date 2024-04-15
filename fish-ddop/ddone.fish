function ddone
	if test -f ./.workspace-marker
		set workspace_path (pwd)
		set origin_path (readlink -f .there)

		if test -e $origin_path
			echo 'Putting you back where you came from'
			cd $origin_path
		else
			echo 'Symlink ".there" to the original folder is missing, putting you pack in home'
			cd $HOME
		end

		set trash_path "/tmp/$USER-wksp-trash"
		mkdir -p $trash_path
		mv $workspace_path $trash_path
	else
		echo 'Not a workspace folder, bailing'
	end
end
