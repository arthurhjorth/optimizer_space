# optimizer_space


Here is a list of the routes that this app opens, and how to use them for NetLogo activities

# get_open_activites() [GET POST]
This returns a LogoList containing [activity_id activity_name]. This can be used by students to set the right activity locally in their netlogo model, so they can upload data to the correct activity.

On the App side, this is wrapped in quotes and escaped a few times, so you can easily retrieve all activites with:

`run-result run-result  item 0 web:make-request "http://<YOUR URL>/get_open_activities" "GET"[] []`
