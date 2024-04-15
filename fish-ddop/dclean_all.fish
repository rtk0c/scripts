function dclean_all
	set trash_path "/tmp/$USER-wksp-trash"
	echo "This is going to delete everything in $trash_path"
	read -l -P 'Do you want to continue? [y/N] ' confirm
	switch $confirm
		case Y y
			rm -rf -v $trash_path
			return 0
		case '' N n
			echo "Bailing"
			return 1
	end
end
