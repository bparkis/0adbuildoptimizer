##0ad Build Optimizer

0ad Build Optimizer is a tool to help you optimize your build orders in the RTS game 0ad. First you write a sequence of commands describing your build order, and then you simulate the outcome of these commands so you can see how you quickly you reach a given population, whether you run out of resources or houses, whether you unintentionally bank up excess resources, etc. Then you edit your build order to fix any problems and improve it.

You could use 0ad itself to do this, playing out your builds manually, but 0ad Build Optimizer has certain advantages.

 * It runs basically instantly, compared to ten minutes or so for a manual 0ad build order. So you can make a change to your build order and immediately see the result.
 * Unlike when you play the build out manually, the 0ad build optimizer doesn't make build order mistakes or deviate from the plan.
 * The "reportSurplus" command can tell you when you have enough spare resources to make a barracks or something without running out of resources later on. You don't want to make a barracks as soon as you have 300 wood - you want to make a barracks when you have enough wood that spending 300 won't interrupt your production.

The downside, of course, is that 0ad Build Optimizer is not a completely perfect simulation of 0ad. Also it takes practice to accurately play a given build order. So it is recommended to manually test and fine-tune your build order in the full game, after designing it with 0ad Build Optimizer.

###How to use it

 * Write your command file, such as builds/mybuild.txt. Use builds/maurya1.txt as an example.
 * Run python3 boom.py builds/mybuild.txt
 * Read the results, see when there is excess or too little of some resource, adjust your command file to fix it, and try again better. Repeat until it's good.
 * Write down/memorize the important parts of the build order you've designed, like how many workers go on each resource at what times, and when to make each barracks.
 * Practice actually playing your build order in the full 0ad game.

The command file consists of lines, with one command per line. Most commands are Python code that will be executed, to do things like send workers to chop wood or build a house. Each line must be executable by itself. Read builds/maurya1.txt for explanation of the different commands. There is also the "time" command which causes the simulation to run until the specified time.

There are a few simplifying differences from 0ad to be mindful of.

 * Buildings and units exist only at single points. There is no limit on the number of entities that can occupy the same point.
 * If you tell a worker to build a building at a point, they will first walk to the point and see if there is a foundation of the right kind already there. If so, they will help repair the existing foundation. If not, they will place a new one and repair it. Only one foundation of each kind may exist at each point.
 * Gathering does not involve walking back and forth between the dropsite and the resource. Instead, gathering occurs at an empirically-determined rate for the resource that already factors in a typical walk time.
 * If you tell a worker to farm at a point, they will first walk there, then see if there is a cc or farmstead there, and if not, they will build a farmstead. Then they will see if there are enough fields for them to take a spot, and if not, they will build them.


If something funny happens where the regular printout isn't giving you enough information, you may wish to inspect the Python state of the simulation. For this you need to know Python. You can then use the "debugend" command to cause the simulator to throw an exception when it finishes. Then run python3 -m pdb boom.py builds/mybuild.txt , wait for the exception to trigger when the run finishes, and inspect the variables with pdb.


###Todos
* Accurate walk speeds
* The rest of the tech tree
* Gathering from a resource when there is significant walk time to the dropsite
* Penalize woodcutting rate when number of woodcutters is very high
* More accurate farming rate for <5 farmers on a field
* Add approximate walk time between foundations when a unit is building multiple buildings "at a point"
