function ddop 
	set origin_path (pwd)
	set rand (random)
	set workspace_path "/tmp/$USER-wksp$rand"
	if test -d $workspace_path
		dwork
		return
	end

	mkdir $workspace_path
	cd $workspace_path

	# Have a separate file for marking purposes, just to be more unlikely to collide: ".workspace-marker" is a relatively uncommon filename and ".there" is much shorter
	# TODO store the $rand in .workspace-marker and check that is its content in `ddone`
	touch .workspace-marker
	ln -s $origin_path .there
end
