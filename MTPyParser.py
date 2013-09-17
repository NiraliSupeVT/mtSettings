#!/usr/bin/python 
# hahaha, this ain't even nix!



"""
MTPyParser, or MTSettings Parser
or PyMTInfo or whatever :P
by Alexander Mouravieff-Apostol

This program takes as input an MT4 settings export file which
is an html formatted 3+Mb file.
It parses the file into the relevant sections:
* General Settings
* IP Access List
* Data Centers
* Operating Times (Market Hours)
* Holidays
* Symbols & Securities
* Groups
* Managers
* Back up settings
* LiveUpdate
* Synchronization
* Plugin Settings

Ultimately, we will be able to:
* Compare data against DB of group and symbol settings.
* Synchronize DB with group and symbol settings.
* Search for managers with specific permissions or group access
"""

#### IMPORTS
from optparse import OptionParser
import os, fnmatch, sys
from bs4 import BeautifulSoup
from menu_system import menu_system


#### CONTROL VARS
parser=OptionParser()
debug = True
filename = "C:/Program Files (x86)/MetaTrader 4 Administrator/38.76.4.43_4433.htm"
settingDict = {}

# ###############################################################################        

class Manager:
    def __init__(self, bsRow=0):
        """
        Create a manager object.
        Initialize with a bsRow object pointing to the first row of a
        MT4 Manager in an Mt4Admin settings export.
        """
        if bsRow != 0:
            cols = bsRow.findAll('td')
            self.num = int(cols[0].renderContents().strip())
            self.name = cols[1].renderContents().strip()
            self.gPerms = cols[3].renderContents().strip()
            self.roles= bsRow.findNext('tr').contents[1].text.strip().split(',')
        else:
            print "I should raise an error here"
            sys.exit()


    def toString(self):
        return "{} - {}\nGroup Permissions:\n\t{}\nRoles:\n{}".format(
                                        self.num, self.name,
                                        self.gPerms,
                                        '\n\t'.join(self.roles))

    def csvRepr(self):
        return "{};{};{};{}".format(self.name, self.num, self.gPerms, self.roles)


    def canViewGroup(self, groupName):
        """
        Returns True if the manager can see groupName.
        Return False if not.
        """
        match=False # by default, one cannot see a group.
        for gp in self.gPerms.split(','):
            if gp == '': continue
            if gp[0]=="!": #exclusion, any matches here block the manager from seeing the group.
                if fnmatch.fnmatch(groupName, gp[1:]):
                    #toScreen("\tExcluded because {} matched {}".format(gp, groupName), 1)
                    return False
            else:
                if fnmatch.fnmatch(groupName, gp):
                    match = True
                    #toScreen("\t{} matches {}.  Looking good.".format(gp, groupName), 1)
        return match

# ###############################################################################        

class mtGroup:
    def __init__(self, bsRow=0):
        """
        bs row structure:
        row 1 (class g) -
            name, company, enabled, adv sec, currency, def deposit, def leverage, annual interest rate
        row 2 -
            "Permissions", permissions (dict, then list with '.' separator
        row 3 - more perms...
            (nothing), list settings with '.' separator
        row 4 -
            "Archiving", settings
        row 5 -
            "Margins", dict format (key : val , key : val, key: val .)
        row 6 -
            Securities, table
            securities table:
                row 1 (class g):
                    secName, enabled, trade, exec style, spread, close by, multi close, auto closeout, tradesizes, commission, taxes, agent
                        tradesizes = double min - double max (double step)
                        commission / agent = x.xxxxxx$/pt/% per lot
                row 2:
                    "maximum deviation:", x pts.
        row 7 - Reports, list with '.' separator
        row 8 - Signature, multi line string          
        """
        if bsRow != 0:
            cols = bsRow.findAll('td')
            self.name = cols[0].renderContents().strip()
            self.company = cols[1].renderContents().strip()
            self.enabled = True
            if cols[2].renderContents().strip()=="No":
                self.enabled = False
            self.currency = cols[4].renderContents().strip()
            
            #Permission strings
            row2 = bsRow.next_sibling
            self.perm1 = row2.contents[1].text.strip()

            #Permissions 2 row
            row3= row2.findNextSibling('tr')
            self.perm2 = row3.contents[1].text.strip()
            

            #Archiving Settings
            row4 = row3.findNextSibling('tr')
            self.archiving = row4.contents[1].text.strip()

            #Margins Settings
            row5 = row4.findNextSibling('tr')
            self.margins = row5.contents[1].text.strip()

            #Row 6 - Security Table
            row6 = row5.findNextSibling('tr')
            #self.secTable = gSecTable(row6.contents[1]) #shld be a table.

            #Row 7 - Reports Settings
            row7 = row6.findNextSibling('tr')
            self.reports = row7.contents[1].text.strip()
            
            #Row 8 - Signature String
            row8 = row7.findNextSibling('tr')
            if row8.contents[0].text.strip() == "Signature:":
                self.signature= row8.contents[1].text.strip()
            else:
                self.signature = ""
        else:
            print "I should raise an error here"
            sys.exit()

    def toString(self):
        retStr= "{:20} - {:20} - {:5} - {}".format(
                                        self.name, self.company,
                                        self.currency, self.enabled)
        retStr= retStr + "\n\tPerms1: {}\n\tPerms2: {}\n\tArchiving: {}\n\tMargins: {}\n\tReports: {}\n\tSignature: {}".format (
                            self.perm1, self.perm2, self.archiving, self.margins, self.reports, self.signature
                            )
        return retStr

# ###############################################################################        

class gSecTable:
    """
    this will be a securities table class.
    securities table:
                    row 1 (class g):
                        secName, enabled, trade, exec style, spread, close by, multi close, auto closeout, tradesizes, commission, taxes, agent
                            tradesizes = double min - double max (double step)
                            commission / agent = x.xxxxxx$/pt/% per lot
                    row 2:
                        "maximum deviation:", x pts.
    """
    def __init__(self, tablediv=0):
         print tablediv
         table = tablediv.findChild('table')
         print table
         sys.exit

# ###############################################################################        

class MTSettings:
    def __init__(self, filep=filename, verbose=False):
        self.bs = BeautifulSoup(open(filename, 'r'))
        self.managerTable = None
        self.groupTable = None
        self.common = None

        self.managers = self.getAllManagers()
        #self.groups = self.getAllGroups()
        

    def importCommon(self):
        #find the commonsettings table.
        for table in self.bs.find_all('table'):
            if table.parent.name=='br':
                tableTitle = table.find('td', class_="lb")
                if tableTitle is None:            
                    toScreen("Common Settings",1)

    def importManagers(self):
        managerTable=None
        for table in self.bs.find_all('table'):
            if table.parent.name=='br':
                tableTitle = table.find('td', class_="lb")
                if tableTitle is not None:
                    if tableTitle.text[0:8] == "Managers":  
                        toScreen("Found it",1)
                        self.managerTable = table
        print self.managerTable.find('td', class_="lb").text
        


    def importGroups(self):
        groupTable = None
        for table in self.bs.find_all('table'):
            if table.parent.name=='br':
                tableTitle = table.find('td', class_="lb")
                if tableTitle is not None:
                    if tableTitle.text[0:6] == "Groups":  
                        toScreen("Found it",1)
                        toScreen(tableTitle.text,1)
                        self.groupTable = table
        print self.groupTable.find('td', class_="lb").text

    def getAllGroups(self):
        """
        Returns a list of group objects.
        """
        #If there is no manager table yet, go import it.
        if self.groupTable == None:
            self.importGroups()

        gList = []

        for row in self.groupTable.find_all('tr', class_='g'):
            if row.parent.parent.name == 'br':
                gList.append(mtGroup(row))
        
        return gList

    def getAllManagers(self):
        """
        Returns a list of manager objects.
        """
        #If there is no manager table yet, go import it.
        if self.managerTable == None:
            self.importManagers()

        manList = []

        for row in self.managerTable.find_all('tr', class_='g'):
            if row.parent.parent.name == 'br':
                manList.append(Manager(row))
        return manList


    def getGroupList(self, matchStr=',*,'):
        """
        Returns the subset of all the defined groups that match the matchStr
        To get all groups, use the default value for matchStr by calling the method
        without any args.
        """
        if self.groupTable == None:
            self.groups = self.getAllGroups()

        gList = []

        for g in self.groups:
            if self.checkGPerm(g.name, matchStr):
                gList.append(g)

        return gList

    


    def checkGPerm(self, groupName, gPerm=''):
        """
        Returns True if the manager can see groupName.
        Return False if not.
        """
        match=False # by default, one cannot see a group.
        for gp in gPerm.split(','):
            if gp == '': continue
            if gp[0]=="!": #exclusion, any matches here block the manager from seeing the group.
                if fnmatch.fnmatch(groupName, gp[1:]):
                    #toScreen("\tExcluded because {} matched {}".format(gp, groupName), 1)
                    return False
            else:
                if fnmatch.fnmatch(groupName, gp):
                    match = True
                    #toScreen("\t{} matches {}.  Looking good.".format(gp, groupName), 1)
        return match
        
        
    def getManagerGroupPermissions(self, manToFind=0, groupToMatch=""):
        """
        Returns a list of managers
        Managers are: 2 rows.
        R1:  #, name, mailbox, groups, ip-filter
        R2:  [empty td] perms.
        R3: Optional:  label, table of security perms.
        """
        #If there is no manager table yet, go import it.
        if self.managerTable == None:
            self.importManagers()

        mans = {}  # format is:  {'314' : {'name':'Alex', 'gPerms':',fishfries,ydx,', 'roles':'dealer, market watch, etc'}}

        #Now....what were we doing?        
        if manToFind == 0 and groupToMatch=="": #just want the full list.
            return self.managers
                
        elif manToFind != 0:  #find a specific manager and display its info.
            toScreen("Searching for a match for {}".format(manToFind))
            for man in self.managers:
                if man.num == manToFind:
                    return man
            return 0
                    
        else:  #find managers with permission to view a given group/MT4groupRE.
            toScreen("Managers who can see {}".format(groupToMatch))
            managersCanSee = []
            for man in self.managers:
                if man.canViewGroup(groupToMatch):
                    toScreen("{:<10} - {} can see {}".format(man.num, man.name, groupToMatch), 1)
                    managersCanSee.append( man )
            return managersCanSee
                    
 
    def writeManagersCSV(self, filename):
        """
        Rights CSV of manager permissions to filename:
        Name, Number, gPerms, roles
        uses ; as delimiter.
        """
        csvFile = open(filename, 'w')
        for man in self.getAllManagers():
            csvFile.write("{}\n".format(man.csvRepr()))
        csvFile.close()


# ###############################################################################        

def toScreen(str, mode=0):
    """
    str is the string to maybe print.
    mode is the type of data 
        0 : always prints (results of queries, fail msgs, etc)
        1 : debug data, warnings, etc.
    """
    if mode and debug:
        print str
    elif mode==0:
        print str

def useOptParser():
    """
    Sets up the Parser.  
    Must be called from "main"
    """
    parser.add_option("-f", "--file", dest="file", default="", help="Settings file to parse")
    parser.add_option("-v", "--verbose", dest="verbose", default=True, help="Print status/debug messages to stdout")
    (options, args) = parser.parse_args()

    debug = options.verbose
    #check the file name.
    if os.path.exists(options.file):
        filename=options.file
    # otherwise use the default filename

def setUpMenu():
    """
    Sets up a menu so everything doesn't have to be coded into if-main.
    """
    menuMTS = menu_system('Main Menu', '[Enter a letter]> ')   
    menuMTS.add_entry('N', 'Get Manager by Number')
    menuMTS.add_entry('G', 'Get Managers who can see group perm string')
    menuMTS.add_entry('q', 'choose `q\' to quit')

    return str(menuMTS.run())
    
    
def execMenuChoice(strChoice, mtS):
    choiceDict = {
        'N' : getManagerByNum,
        'G' : getManagerByGPerm,
        'Q' : sys.exit
        }

    choiceDict[strChoice[-1]](mtS)
    
def getManagerByNum(mtS):
    ri = raw_input("Use , to separate multiple managers: 100,101\nWhite space doesn't matter\nEnter ManagerNumbers: ")

    rc = raw_input("Do you want formatted text or CSV format? (t for text /c for choice)> ")

    if rc.strip()[0] == 't':
        rc = True
        print "Formatted Text selected"
    elif rc.strip()[0] == 'c':
        rc = False
        print "CSV format selected"
    else:
        print "You did not give a valid (c/t) answer.  Choosing text formatted."
        rc=True

    for mn in ri.split(','):
        try:
            int(mn)
        except ValueError:
            print "\n{} was not valid. Trying next.".format(mn)
            continue

        
            
        m = mtS.getManagerGroupPermissions(manToFind=int(mn))
        if m == 0:
            print 'Could not find Manager {}.'.format(mn)
        else:
            if rc:
                print m.toString()
            else:
                print m.csvRepr()

        ##should this function return the list of managers??
    

def getManagerByGPerm(mtS):
    print "You may enter a groupPermissions string, or a group name."
    print "Ex: ,*, for all groups."
    print "Or: Iam-Micro-USD for just that group."
    print "Get creative!  If you enter a gPerm, you will have the option of \'All\' or \'Any\'"
    print "Selecting ALL will show only managers who can see ALL the groups that match your gPerm"
    print "Selecting ANY will show all manager who can see any group that matches."

    ri = raw_input("Please enter the group string.  ")

    
    matchALL=True #if it's just a single group, match all behavior
    if ',' in ri:
        choice = raw_input("0- Return managers that can see ANY group \n1 - Return only Managers that match ALL groups\nSelect option > ")
        if choice.strip() == '0':
            matchALL = False

    gl = mtS.getGroupList(matchStr=ri)

    ml = mtS.getManagerGroupPermissions()
    
    showManagers=[]
    for m in ml:
        allMatch=True
        for g in gl:
            if matchALL:
                if not m.canViewGroup(g.name):
                    allMatch=False
                    break #one fail is all it takes.
            else: #matchAll is false, so just match ANY:
                if m.canViewGroup(g.name):
                    showManagers.append(m)
                    break #one match is all it takes, move on to next manager
        if matchALL and allMatch:
            showManagers.append(m)

    if matchALL:
        print "You searched for managers able to see ALL of {}".format(ri)
    else:
        print "You searched for managers able to see ANY of {}".format(ri)
    print "There are {} matching managers.".format(len(showManagers))
    for m in showManagers:
        print "{:11} - {} ".format(m.num, m.name)

def compareCoverage(mlist, glist):
    resDict = {}

    for g in glist:
        resDict[g.name]={}
        for m in mlist:
            resDict[g.name][m.num]= m.canViewGroup(g.name)
    return resDict
                
                
    

# ### One Main to Rule them all...
if __name__=="__main__":
    #useOptParser()
    toScreen("Args Parsed")
    toScreen("You are seeing this because verbose is on", 1)
    toScreen("Filename = %s"%filename)
    
    if os.path.exists(filename):
        toScreen("The Filename is good.", 1)
    else:
        toScreen("The file {} does not exist".format(filename))
    mtSettings = MTSettings(filename, debug)


    """
    m = mtSettings.getManagerGroupPermissions(manToFind=100)
    if m == 0:
        print "No match"
    else:
        print m.toString()
        gl = mtSettings.getGroupList()

        print "CANnot SEE GROUPS"
        i=0
        for g in gl:
            if not m.canViewGroup(g.name):
                i=i+1
                print "{}: {}".format(i, g.name)
        print "CANnot see {} of {} groups ({}%)".format(i, len(gl), i*100/len(gl))
    """
    
    #print "\n\nLooking for managers who can see YDX-Std-USD-2"
    #for m in mtSettings.getManagerGroupPermissions(groupToMatch="YDX-Std-USD-2"):
    #    print "{:10} - {}".format(m.num, m.name)

    #debug=False

    #mtSettings.writeManagersCSV("managers.txt")

    """
    groupsToCheck=[
        "YDX-Mic-USD",
        "YDX-Mic-IF-USD",
        "YDX-1p8-USD",
        "YDX-Agents"
        ]

    for g in groupsToCheck:
        mtSettings.getManagerGroupPermissions(groupToMatch=g)
        print "\n\n"
    """
    """
    ml = mtSettings.getManagerGroupPermissions(groupToMatch="PRO-FXR-USD")

    for m in ml:
        if m.num == 100 or m.num==101:
            print m.toString()
    """
 

    
    
    # #########
    # COVERAGE TESTS AND DISPLAYS
    """
    gl = mtSettings.getGroupList()
    bridgeMans = [mtSettings.getManagerGroupPermissions(manToFind=100), mtSettings.getManagerGroupPermissions(manToFind=101)]        
    resDict = compareCoverage(bridgeMans, gl)
    
    print "{:17} | {:5} | {:5} |".format("Group Name", bridgeMans[0].num, bridgeMans[1].num)
    for gname in resDict.keys():
        print "{:17} | {:5} | {:5} |".format(gname, resDict[gname][bridgeMans[0].num], resDict[gname][bridgeMans[1].num])

    dcFlag = False
    for gname in resDict.keys():
        print "{} AND {} = {}".format(resDict[gname][bridgeMans[0].num], resDict[gname][bridgeMans[1].num], resDict[gname][bridgeMans[0].num] and resDict[gname][bridgeMans[1].num])
        if resDict[gname][bridgeMans[0].num] and resDict[gname][bridgeMans[1].num]:
            print "DOUBLE COVERAGE FOR: "+gname
            dcFlag=True
    if not dcFlag:
        print "No double coverages"
    """
    while True:
        if execMenuChoice(setUpMenu(), mtSettings)=="Q":
            break;
    
    #print gl[0].secTable    
    #importSettings()
    toScreen("Goodbye.")
    
