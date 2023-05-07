#!/usr/bin/python3
# ----05-04-2023  9:56:49----

# A simulator to assist in optimizing build orders.
# example usage:
# python3 boom.py builds/maurya1.txt
#
# builds/maurya1.txt is a list of commands describing a build order
# 

import math
from collections import defaultdict
import re

def distance(pos1, pos2):
    return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5

def posEqual(pos1, pos2):
    return pos1[0] == pos2[0] and pos1[1] == pos2[1]

def entitiesAtPosition(actorList, pos):
    return [a for a in actorList if posEqual(a.position, pos)]

def anyEntityAtPosition(actorList, pos):
    result = entitiesAtPosition(actorList, pos)
    if len(result) > 0:
        return result[0]
    return None

# example actions:
# A worker building a building
# A worker harvesting resources
# A worker walking to a point
# A building training a batch
# A building researching a tech
class Action:
    name = "action"
    def act(self, state, actor):
        pass
    def cancel(self, state, actor):
        actor.actionQueue.pop()

class Walk(Action):
    def __init__(self, unit, position):
        self.name = "walk"
        self.position = position
        self.timeDone = distance(position, unit.position)

    def act(self, state, unit):
        if state.time >= self.timeDone:
            unit.position = self.position
            unit.actionQueue.pop()

class Foundation:
    def __init__(self, kind, position, state):
        self.kind = kind
        self.position = position
        self.progress = 0
        self.maxProgress = costs[kind][4]
        self.builders = 0
        self.lastTimestepBuilt = 0
        self.convertedToBuilding = False
        state.addRes(costs[kind], -1)
        state.foundationLists[kind].append(self)
        if kind == "farmstead":
            self.maxFields = 4
            self.fields = 0
            self.farmers = 0

    def rate(self):
        return self.builders ** 0.7

class Build(Action):
    def __init__(self, kind, position, state, repeating = False):
        self.name = "build " + kind
        self.foundation = anyEntityAtPosition(state.foundationLists[kind], position) # if there's already a foundation don't start a new one
        self.kind = kind
        self.startedYet = False
        self.repeating = repeating
        self.position = position

    def act(self, state, unit):
        if self.foundation != None:
            assert(posEqual(unit.position, self.foundation.position))
        if not self.startedYet:
            # current foundation to work on at this position?
            if self.foundation == None:
                self.foundation = anyEntityAtPosition(state.foundationLists[self.kind], self.position)
            if self.foundation == None:
                self.foundation = Foundation(self.kind, self.position, state)
            self.foundation.builders += 1
            self.startedYet = True
        if self.foundation.lastTimestepBuilt != state.time:
            self.foundation.lastTimestepBuilt = state.time
            self.foundation.progress += self.foundation.rate()
        if self.foundation.progress >= self.foundation.maxProgress:
            if not self.foundation.convertedToBuilding:
                state.buildingLists[self.foundation.kind].append(Building(self.foundation.kind, self.foundation.position))
                self.foundation.convertedToBuilding = True
                state.foundationLists[self.foundation.kind].remove(self.foundation)
                if self.foundation.kind == "house":
                    state.maxPop += HOUSEPOP
                print(unit.kind, "finished", self.foundation.kind)
            if self.repeating:
                self.startedYet = False
                # first see if another worker already started the same kind of foundation here
                foundations = [f for f in state.foundationLists[self.foundation.kind] if posEqual(f.position, self.foundation.position)]
                if len(foundations) > 0:
                    self.foundation = foundations[0]
                else:
                    self.foundation = Foundation(self.foundation.kind, self.foundation.position, state)
                # and we'll continue on the new foundation
            else:
                unit.actionQueue.pop()

def setSimpleAction(state, unit, pos, actionName):
    "Used when a building has set a waypoint for trained units."
    if actionName == "walk":
        state.walk([unit], pos)
    elif actionName == "chop":
        state.chop([unit], pos)
    elif actionName == "farm":
        state.farm([unit], pos)
    elif actionName == "berries":
        state.berries([unit], pos)
    elif actionName == "chicken":
        state.chicken([unit], pos)

class WaypointSchedule:
    def __init__(self, schedule):
        "schedule is a list of (pop, waypoint) in ascending order of pop. The waypoint applies if the current population is >= pop, and < the pop of the next entry."
        self.schedule = schedule
        self.schedule.sort() # just in case

    def getWaypoint(self, population):
        okay = False
        for i, (pop, waypoint) in enumerate(self.schedule):
            if population >= pop:
                okay = True
            elif okay:
                return self.schedule[i-1][1]
        if okay:
            return self.schedule[-1][1]
        return ((0,0), None)

def findMaxBatch(resources, cost, availablePop):
    limit = availablePop
    for r,c in zip(resources[:4], cost[:4]):
        if c == 0:
            continue
        limit2 = r // c
        if limit2 < limit:
            limit = limit2
    return int(limit)

class Train(Action):
    def __init__(self, unitkind, count=1, waypoint = ((0, 0), None), repeating=False, maxBatching=False):
        self.name = "train " + unitkind
        self.unitkind = unitkind
        self.count = count
        self.maxCount = count
        self.repeating = repeating
        self.timer = 0
        self.maxTimer = math.ceil(costs[unitkind][4] * count**0.8)
        self.waypoint = waypoint
        self.maxBatching = maxBatching

    def act(self, state, building):
        if self.timer == 0:
            if self.maxBatching:
                self.count = min(findMaxBatch(state.resources, costs[self.unitkind], state.maxPop - state.pop), self.maxCount)
                self.maxTimer = math.ceil(costs[self.unitkind][4] * self.count**0.8)
            state.addRes(costs[self.unitkind], -self.count)
            state.pop += self.count
        self.timer += 1
        if self.timer > self.maxTimer:
            for i in range(self.count):
                unit = Actor(self.unitkind, building.position)
                state.workers.append(unit)
                waypoint = self.waypoint
                if waypoint[1] == None and building.waypointSchedule != None:
                    waypoint = building.waypointSchedule.getWaypoint(len(state.workers))
                if waypoint[1] == None:
                    waypoint = building.waypoint
                if waypoint[1] != None:
                    print("Using waypoint " + waypoint[1] + " for unit " + str(len(state.workers)))
                    setSimpleAction(state, unit, waypoint[0], waypoint[1])
            self.timer = 0
            if not self.repeating:
                building.actionQueue.pop()

    def cancel(self, state, building):
        if self.timer != 0: # currently making a batch we can reimburse
            state.addRes(costs[self.unitkind], self.count)
            state.pop -= self.count
        building.actionQueue.pop()

class Research(Action):
    def __init__(self, techName):
        self.name = "research " + techName
        self.timer = 0
        self.techName = techName
        self.maxTimer = costs[techName][4]

    def act(self, state, building):
        if self.timer == 0:
            state.addRes(costs[self.techName], -1)
        self.timer += 1
        if self.timer > self.maxTimer:
            state.upgrades.append(self.techName)
            building.actionQueue.pop()

    def cancel(self, state, building):
        if self.timer != 0:
            state.addRes(costs[self.techName])
        building.actionQueue.pop()
    

class Gather(Action):
    def __init__(self, pos, resourceIndex, gatherType):
        self.position = pos
        self.resourceIndex = resourceIndex
        self.resource = 0
        self.gatherType = gatherType
        self.name = gatherType

    def takeResource(self, state, amount):
        return amount

    def act(self, state, unit):
        assert(posEqual(unit.position, self.position))
        rate = state.gatherRate(self.gatherType, unit)
        carryCapacity = state.carryCapacity(unit)
        qty = self.takeResource(state, rate)
        if qty == 0: # resource depleted
            state.resources[self.resourceIndex] += self.resource
            unit.actionQueue.pop()
            return
        state.income[self.resourceIndex] += qty
        self.resource += qty
        if self.resource >= carryCapacity:
            state.resources[self.resourceIndex] += self.resource
            self.resource = 0

    def cancel(self, state, unit):
        state.resources[self.resourceIndex] += self.resource
        unit.actionQueue.pop()

class DepletableGather(Gather):
    def __init__(self, gatherableList, pos, resourceIndex, gatherType):
        super().__init__(pos, resourceIndex, gatherType)
        fs = [f for f in gatherableList if posEqual((f[0], f[1]), pos)]
        assert(len(fs) > 0)
        self.gatherable = fs[0]
        
    def takeResource(self, state, amount):
        if self.gatherable[2] >= amount:
            self.gatherable[2] -= amount
            return amount
        if self.gatherable[2] > 0:
            tmp = self.gatherable[2]
            self.gatherable[2] = 0
            return tmp
        return 0

class Chop(DepletableGather):
    def __init__(self, state, pos):
        super().__init__(state.forestList, pos, WOOD, "chop")
        
class Berries(DepletableGather):
    def __init__(self, state, pos):
        super().__init__(state.berriesList, pos, FOOD, "berries")

class Chicken(DepletableGather):
    def __init__(self, state, pos):
        super().__init__(state.chickenList, pos, FOOD, "chicken")
        
    # TODO make sure there's an elephant or storehouse at the
    # gather position, and a forest.

# Build some number of fields around a cc or farmstead
# (also building the farmstead if necessary)
# until there are enough fields for us to take a spot
# and begin farming
class BuildFields(Action):
    def __init__(self, pos):
        self.name = "build fields"
        self.position = pos
        self.rank = None
        self.buildAction = None

    def act(self, state, unit):
        if self.rank == None:
            state.farmerRanks[self.position] += 1
            self.rank = state.farmerRanks[self.position]
        if self.position != (0,0):
            farmstead = anyEntityAtPosition(state.buildingLists["farmstead"], self.position)
            if farmstead == None:
                unit.actionQueue.append(Build("farmstead", self.position, state))
                return
                
        num_fields = len(entitiesAtPosition(state.buildingLists["field"], self.position))
        if num_fields * 5 >= self.rank:
            unit.actionQueue.pop()
            assert(unit.actionQueue[-1].name == "farm")
            return
        unit.actionQueue.append(Build("field", self.position, state))
        
class Farm(Gather):
    def __init__(self, position):
        super().__init__(position, FOOD, "farm")
        self.position = tuple(position)
        self.started = False

    def cancel(self, state, actor):
        # this was previously set during the State.farm() command
        self.farmers[self.position] -= 1
        super().cancel(state, actor)

# A unit or building.
class Actor:
    def __init__(self, kind, position = None):
        self.kind = kind # a string, "male" "female" "horse" "elephant" for units. Could also be building.
        if position == None:
            self.position = [0, 0] # Scaled so that distance = male or female walking time
        else:
            self.position = position
        self.actionQueue = []

    def clearActionQueue(self, state):
        if self.actionQueue == []:
            return
        self.actionQueue[-1].cancel(state, self)
        self.actionQueue.clear()

class Building(Actor):
    def __init__(self, kind, position = None):
        super().__init__(kind, position)
        self.waypoint = self.position, None
        self.waypointSchedule = None

FOOD = 0
WOOD = 1
STONE = 2
METAL = 3
HOUSEPOP = 5

resourceNames = ["food", "wood", "stone", "metal"]

state = None

class State:
    def __init__(self, commandFile):
        # food, wood, stone, metal
        self.resources = [300, 300, 300, 300]

        # for reporting purposes
        self.income = [0, 0, 0, 0]
        
        self.workers = [Actor(w) for w in "horse male male male male female female female female elephant".split()]
        self.previousUnitSelection = []
        self.pop = len(self.workers)
        self.maxPop = 20

        self.cc = Building("cc")
        self.cc.fields = 0
        self.cc.maxFields = 6
        self.cc.farmers = 0
        # map from position to number of assigned farmers at that position
        self.farmers = defaultdict(int)
        # map from position to number of farmers that already arrived at that position, for giving priority to fields
        self.farmerRanks = defaultdict(int)

        # map from building kind to list of buildings with that kind
        self.buildingLists = defaultdict(list)
        self.buildingLists["cc"] = [self.cc]
        # map from foundation kind to list of foundations with that kind
        self.foundationLists = defaultdict(list)

        # x, y, amount of wood
        self.forestList = []
        # x, y, amount of food
        self.berriesList = []
        self.chickenList = []

        self.upgrades = []
        self.time = 0 # seconds

        # Directives for automatic actions
        self.desiredFoodRatio = 0.5

        self.commands = open(commandFile).read().split("\n")

        self.summaryPeriod = 10
        self.debugEnd = False
        self.reportSurplus = None
        self.surplusStep = 0
        self.stopwhen = "False"

    def tellAboutSurplus(self):
        if self.reportSurplus != None:
            f, w, s, m = self.reportSurplus
            if self.surplusStep != 0:
                print("Surplus of", "{0:.0f}f {1:.0f}w {2:.0f}s {3:.0f}m".format(f, w, s, m), "occurred first at", "{0:03d}:{1:02d}".format(self.surplusStep // 60, self.surplusStep % 60), "and continued until the end.")
            else:
                print("No sustained surplus of", "{0:.0f}f {1:.0f}w {2:.0f}s {3:.0f}m".format(f, w, s, m))
        

    def checkOK(self, stopwhen):
        result = True, ""
        for i in range(4):
            if self.resources[i] < 0:
                f, w, s, m = self.resources
                print("Resources went below 0: {0:.0f}f {1:.0f}w {2:.0f}s {3:.0f}m".format(f, w, s, m))
                result = False
        if self.pop > self.maxPop:
            print("Not enough houses.")
            result = False
        if eval(stopwhen) == True:
            print("Hit stop condition: " + stopwhen)
            result = False
        if result == False:
            self.summary()
            self.tellAboutSurplus()
            if self.debugEnd:
                raise Exception("Run finished.")
        return result

    def addRes(self, resources, multiplier=1):
        for i in range(4):
            self.resources[i] += resources[i] * multiplier

    def gatherRate(self, gatherType, unit):
        "per second gather rate, including walk time etc"
        if gatherType == "chop":
            if unit.kind == "male":
                w = 0.63
            else:
                w = 0.53
            if "up_wood3" in self.upgrades:
                w *= 1.25
            if "up_wood2" in self.upgrades:
                w *= 1.25
            if "up_wood1" in self.upgrades:
                w *= 1.25
            return w
        elif gatherType == "farm":
            r = 0.43
            if "up_farm3" in self.upgrades:
                r *= 1.2
            if "up_farm2" in self.upgrades:
                r *= 1.2
            if "up_farm1" in self.upgrades:
                r *= 1.2
        elif gatherType == "chicken":
            return 3
        elif gatherType == "berries":
            if "up_gather" in self.upgrades:
                return 1.25
            return 0.86
        return 0.5

    def carryCapacity(self, unit):
        if unit.kind == "horse":
            return 20
        return 10

    def summary(self):
        idle, farmers, choppers, builders, women = 0, 0, 0, 0, 0
        for w in self.workers:
            if w.kind == "female":
                women += 1
            if len(w.actionQueue) == 0:
                idle += 1
                continue
            actionName = w.actionQueue[-1].name
            if actionName[:5] == "build":
                builders += 1
            elif actionName[:4] == "farm":
                farmers += 1
            elif actionName[:4] == "chop":
                choppers += 1
        idleBuildings = 0
        for b in [self.cc] + self.buildingLists["barracks"]:
            if b.actionQueue == []:
                idleBuildings+=1
                
        print("{12:03d}:{13:02d} {0:.0f}f+{15:.0f} {1:.0f}w+{16:.0f} {2:.0f}s+{17:.0f} {3:.0f}m+{18:.0f} {4}/{5}pop {11}women {6}idle {7}farm {8}chop {9}build {10}barracks {14}idlebarracks/cc".format(self.resources[0], self.resources[1], self.resources[2], self.resources[3], self.pop, self.maxPop, idle, farmers, choppers, builders, len(self.buildingLists["barracks"]), women, self.time // 60, self.time % 60, idleBuildings, self.income[0]*60, self.income[1]*60, self.income[2]*60, self.income[3]*60))

    def preprocessCommand(self, command):
        "Add self. so the user doesn't have to put that everywhere in the command file."
        selfcommands = "selectWorkers previousWorkerSelection selectBuilding build walk chop berries chicken farm train research setWaypoint setWaypointSchedule".split()
        for c in selfcommands:
            pattern = r"\b" + c + r"\s*\("
            command = re.subn(pattern, "self." + c + "(", command)[0]
        return command

    def step(self, stepCommands):
        "Advance game time by one second. Returns False if done."
        if self.time % self.summaryPeriod == 0:
            self.summary()
        if self.reportSurplus != None:
            isAboveLevel = True
            for i in range(4):
                if self.resources[i] < self.reportSurplus[i]:
                    isAboveLevel = False
            if self.surplusStep == 0:
                if isAboveLevel:
                    self.surplusStep = self.time
            else:
                if not isAboveLevel:
                    self.surplusStep = 0
                
        self.income = [0, 0, 0, 0]
        for command in stepCommands:
            exec(self.preprocessCommand(command))
        for worker in self.workers:
            if self.time == 15 and worker.kind == "elephant":
                assert(worker.actionQueue != [])
            if worker.actionQueue != []:
                worker.actionQueue[-1].act(self, worker)
        for buildingKind in self.buildingLists:
            for building in self.buildingLists[buildingKind]:
                if building.actionQueue != []:
                    building.actionQueue[-1].act(self, building)
        self.time += 1
        return self.checkOK(self.stopwhen)

    def doCommands(self):
        "execute all commands in the command file"
        stopTime = 0
        stepCommands = []
        for command in self.commands:
            command = command.split("#")[0]
            if command[:5] == "time ":
                nums = command.split(" ")[1].split(":")
                stopTime = int(nums[0]) * 60 + int(nums[1])
                if not self.step(stepCommands):
                    return
                while self.time < stopTime:
                    if not self.step([]):
                        return
                stepCommands.clear()
            elif command[:7] == "skipby ":
                self.summaryPeriod = int(command.split(" ")[1])
            elif command[:7] == "forest ":
                self.forestList.append(list(map(int, command.split()[1:4])))
            elif command[:8] == "berries ":
                self.berriesList.append(list(map(int, command.split()[1:4])))
            elif command[:8] == "chicken ":
                self.chickenList.append(list(map(int, command.split()[1:4])))
            elif command[:9] == "stopwhen ":
                stopwhen = command[9:]
            elif command[:8] == "debugend":
                self.debugEnd = True
            elif command[:14] == "reportsurplus ":
                _, f, w, s, m = command.strip().split()
                self.reportSurplus = [int(r.strip()) for r in [f, w, s, m]]
            else:
                if command.strip() != "" and command.strip()[0] != "#":
                    stepCommands.append(command)
        # if we weren't given an end time, run until at least 15 minutes
        if stepCommands != []:
            if not self.step(stepCommands):
                return
            while self.time < 900:
                if not self.step([]):
                    return
        self.tellAboutSurplus()
        if self.debugEnd:
            raise Exception("Run finished.")


    # commands that the user may issue and we will exec()
    def selectWorkers(self, kinds, action=None, num=None, pos=None):
        k = kinds.split()
        def filter(w):
            if kinds != None and not w.kind in k:
                return False
            if pos != None and w.pos != pos:
                return False
            if action != None:
                if action == "idle":
                    if w.actionQueue != []:
                        return False
                elif w.actionQueue == []:
                    return False
                elif w.actionQueue[-1].name != action:
                    return False
            return True
        result = [w for w in self.workers if filter(w)]
        if num == None:
            self.previousSelection = result
            return result
        self.previousSelection = result[:num]
        return result[:num]

    def previousWorkerSelection(self):
        return self.previousSelection
    
    def selectBuilding(self, kind, pos=None, num=None):
        if num != None:
            return self.buildingLists[kind][num-1]
        buildings = [b for b in self.buildingLists[kind] if pos == None or posEqual(b.position, pos)]
        # give priority to idle buildings
        idleBuildings = [b for b in buildings if b.actionQueue == []]
        if idleBuildings != []:
            return idleBuildings[0]
        return buildings[0]

    def build(self, workers, kind, pos=None, repeating=False, queued=False):
        if pos == None:
            pos = workers[0].position
        for w in workers:
            if not queued: w.clearActionQueue(self)
            w.actionQueue.insert(0, Walk(w, pos))
            w.actionQueue.insert(0, Build(kind, pos, self, repeating))

    def walk(self, workers, pos, queued=False):
        for w in workers:
            if not queued: w.clearActionQueue(self)
            w.actionQueue.insert(0, Walk(w, pos))

    def gatherHelper(self, pos, kinds, workers, gatherFn, gatherableList, queued):
        if pos == None:
            pos = [(f[0], f[1]) for f in gatherableList if f[2] > 0][0]
        for w in workers:
            if not queued: w.clearActionQueue(self)
            w.actionQueue.insert(0, Walk(w, pos))
            w.actionQueue.insert(0, gatherFn(self, pos))
        
    def chop(self, workers, pos=None, queued=False):
        self.gatherHelper(pos, "male female", workers, lambda a, b: Chop(a, b), self.forestList, queued)

    def berries(self, workers, pos=None, queued=False):
        self.gatherHelper(pos, "female", workers, lambda a, b: Berries(a, b), self.berriesList, queued)
    
    def chicken(self, workers, pos=None, queued=False):
        self.gatherHelper(pos, "horse", workers, lambda a, b: Chicken(a, b), self.chickenList, queued)

    def farm(self, workers, pos=None, queued=False):
        for w in workers:
            self.farmHelper(w, pos, queued)

    def farmHelper(self, w, pos=None, queued=False):
        def allowedFields(dropsiteKind):
            if dropsiteKind == "cc":
                return 6
            return 4
        highestFarmsteadCoordinate = 0
        if pos == None:
            if self.farmers[(0,0)] + 1 <= allowedFields("cc") * 5:
                pos = 0,0
            else:
                for farmstead in self.buildingLists["farmstead"] + self.foundationLists["farmstead"]:
                    if farmstead.position[1] > highestFarmsteadCoordinate:
                        highestFarmsteadCoordinate = farmstead.position[1]
                    if self.farmers[tuple(farmstead.position)] + 1 <= allowedFields("farmstead") * 5:
                        pos = farmstead.position
                        break
            if pos == None:
                pos = (0, highestFarmsteadCoordinate + 2)
        else:
            if posEqual(pos, (0,0)):
                assert(self.farmers[(0,0)] + 1 <= allowedFields("cc") * 5)
            else:
                assert(self.farmers[tuple(pos)] + 1 <= allowedFields("farmstead") * 5)
        pos = tuple(pos)
        self.farmers[pos] += 1
        if not queued: w.clearActionQueue(self)
        w.actionQueue.insert(0, Walk(w, pos))
        # also may build a farmstead if necessary
        w.actionQueue.insert(0, BuildFields(pos))
        w.actionQueue.insert(0, Farm(pos))

    def train(self, building, unitKind, numUnits, repeating=False, queued=False, waypoint=((0,0), None), maxBatching = False):
        if not queued: building.clearActionQueue(self)
        building.actionQueue.insert(0, Train(unitKind, numUnits, waypoint, repeating, maxBatching))

    def research(self, building, techName, queued=False):
        assert(costs[techName][5] == building.kind)
        if not queued: building.clearActionQueue(self)
        building.actionQueue.insert(0, Research(techName))

    def setWaypoint(self, building, pos, command="walk"):
        "Supported: walk berries chicken chop farm"
        building.waypointSchedule = None
        building.waypoint = pos, command

    def setWaypointSchedule(self, building, schedule):
        "Supported: walk berries chicken chop farm"
        building.waypoint = building.position, None
        if schedule == None:
            building.waypointSchedule = None
        else:
            building.waypointSchedule = WaypointSchedule(schedule)

# maps an unit or building to the resources needed to train/build it.  [food, wood, stone, metal, time]
costs = {}
costs["horse"] = [100,50,0,0,15]
costs["sheep"] = [50,0,0,0,40]
costs["male"] = [50,50,0,0,10]
costs["female"] = [50,0,0,0,8]
costs["trader"] = [100,0,0,80,15]
costs["champ"] = [150,80,0,100,25]
costs["elephant"] = [100,0,0,0,11]
units = "horse sheep man woman trader champ".split()

costs["house"] = [0, 75, 0, 0, 30]
costs["storehouse"] = [0, 100, 0, 0, 40]
costs["farmstead"] = [0, 100, 0, 0, 45]
costs["cc"] = [0, 300, 300, 250, 500]
costs["corral"] = [0, 100, 0, 0, 50]
costs["barracks"] = [0, 300, 0, 0, 150]
costs["temple"] = [0, 0, 300, 0, 200]
costs["market"] = [0, 300, 0, 0, 150]
costs["blacksmith"] = [0, 200, 0, 0, 120]
costs["tower"] = [0, 100, 100, 0, 150]
costs["field"] = [0,100,0,0,50]
costs["castle"] = [0, 300, 600, 0, 450]
structures = "house storehouse farmstead cc corral barracks temple market blacksmith tower field castle".split()

costs["up_chop1"] = [ 0, 200, 0, 100, 40, "storehouse"]
costs["up_chop2"] = [ 0, 400, 0, 200, 50, "storehouse"]
costs["up_chop3"] = [ 0, 600, 0, 300, 60, "storehouse"]
costs["up_stone1"] = [ 200, 0, 100, 0, 40, "storehouse"]
costs["up_stone2"] = [ 300, 0, 200, 0, 50, "storehouse"]
costs["up_stone3"] = [ 400, 0, 300, 0, 60, "storehouse"]
costs["up_metal1"] = [ 200, 0, 0, 100, 40, "storehouse"]
costs["up_metal2"] = [ 300, 0, 0, 200, 50, "storehouse"]
costs["up_metal3"] = [ 400, 0, 0, 300, 60, "storehouse"]
costs["up_gather"] = [ 0, 100, 0, 0, 40, "farmstead"]
costs["up_farm1"] = [ 0, 200, 0, 100, 40, "farmstead"]
costs["up_farm2"] = [ 0, 300, 0, 100, 50, "farmstead"]
costs["up_farm3"] = [ 0, 400, 0, 100, 60, "farmstead"]
costs["up_trade1"] = [ 0, 150, 0, 150, 40, "market"]
costs["up_trade2"] = [ 0, 300, 0, 300, 40, "market"]


import sys

if __name__== "__main__":
    if len(sys.argv) != 2:
        print("Usage: python boom2.py <commandfile>")
        quit()
    filename = sys.argv[1]
    state = State(filename)
    cc = state.cc
    state.doCommands()
    
