function dclean_all
	set trash_path "/tmp/$USER-wksp-trash"
	echo "This is going to delete everything in $trash_path"
	if read_confirm
		rm -rf -v $trash_path
	else
		echo "Bailing"
	end
end
