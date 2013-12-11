#!/usr/bin/python
import subprocess
import flask
from vnetmanager import db, app
from vnetmanager.models import *

class FlowPusher(object):
    def __init__(self):
        switches = NetworkSwitch.query.all()
        self.BroadcastIntPortList = {};
        self.BroadcastExtPortList = {};

        for switch in switches:
            port = [None]
            self.BroadcastIntPortList[switch.swid] = port
        for switch in switches:
            blah = [None]
            self.BroadcastExtPortList[switch.swid] = blah

    def pushflow(self, swid, flowstrs):
        with open("/tmp/flow", "wb") as fo:
            for flows in flowstrs:
                print 'Flows------------ {}'.format(flows) 
                fo.writelines(flows)
        subprocess.call(['sudo', 'ovs-ofctl', 'add-flows', swid, '/tmp/flow'])

    def broadcastFlows(self, switch, priority, vlan, ext=False):
        flowstrs = []
        swflow = []
        if ext == True:
            portlist = ''
            print 'switch {} int port list {} ext port list {}'.format(switch,self.BroadcastIntPortList[switch],self.BroadcastExtPortList[switch])
            for port in self.BroadcastIntPortList[switch]:
                if port is not None:
                    for extport in self.BroadcastExtPortList[switch]:
                        if extport is not None:
                            swflow = 'table=1, priority={}, in_port={}, dl_vlan={}, dl_dst=ff:ff:ff:ff:ff:ff, actions=output:{}\n'.format(priority,port,vlan,extport)
                    flowstrs.append(swflow)
            portlist = ''
            for port in self.BroadcastExtPortList[switch]:
                if port is not None:
                    portlist += str(port)
                    portlist += ','
            swflow = 'table=1, priority={}, dl_vlan={}, dl_dst=ff:ff:ff:ff:ff:ff, actions=output:{}\n'.format(99,vlan,portlist)
            flowstrs.append(swflow)
        else:
            portlist = ''
            for port in self.BroadcastIntPortList[switch]:
                if port is not None:
                    portlist += str(port)
                    portlist += ','
            print 'Internal ports broadcast flows ports {}'.format(portlist)
            swflow = 'table=1, priority={},dl_vlan={}, dl_dst=ff:ff:ff:ff:ff:ff, actions=strip_vlan,output:{}\n'.format(priority,vlan,portlist)
            flowstrs.append(swflow)
        self.pushflow(switch,flowstrs)

    def addflow(self, switch, mac, vlan, port):
        flowstrs = []
        #port = []
        print 'Adding individual flows per mac switch {} port {}'.format(switch,port)
        swflow = 'table=0, priority=100, in_port={}, vlan_tci=0,dl_src={}, actions=mod_vlan_vid:{},resubmit(,1)\n'.format(port,mac,vlan)
        flowstrs.append(swflow)
        swflow = 'table=1, priority=100, dl_vlan={}, dl_dst={}, actions=strip_vlan,output:{}\n'.format(vlan, mac, port)
        flowstrs.append(swflow)
        self.pushflow(switch,flowstrs)
        
        if port not in self.BroadcastIntPortList[switch]:
            self.BroadcastIntPortList[switch].append(port)
        self.broadcastFlows(switch,100,vlan,False)
        print 'swich {} int port list {}'.format(switch,self.BroadcastIntPortList[switch])

    def createAndAddSwitchFlows(self,switchlist,srcmac,dstmac,vlan):
        flowstrs = []
        swflow = ''
        print 'src mac {} dst mac {}'.format(srcmac,dstmac)
        srcswitch = NetworkSwitch.query.filter_by(swid = switchlist[0]).first()
        dstswitch = NetworkSwitch.query.filter_by(swid = switchlist[1]).first()
        extport = srcswitch.links.filter_by(dstswitch_id = dstswitch.id).first().srcswitch_port
        print 'BBBEEEEE swich {} int port list {}'.format('s2',self.BroadcastIntPortList['s2'])

        swflow = 'table=1, priority=100,dl_vlan={}, dl_dst={}, actions=output:{}\n'.format(vlan,dstmac,extport)
        flowstrs.append(swflow)
        swflow = 'table=0, priority=99, in_port={}, actions=resubmit(,1)\n'.format(extport)
        flowstrs.append(swflow)
        self.pushflow(switchlist[0],flowstrs)
        if extport not in self.BroadcastExtPortList[switchlist[0]]:
            self.BroadcastExtPortList[switchlist[0]].append(extport)
            print 'Ext port list for switch {} is {}'.format(switchlist[0],self.BroadcastExtPortList[switchlist[0]])
        self.broadcastFlows(switchlist[0],101,vlan,True)

        flowstrs = []
        swflow = ''
        srcswitch = NetworkSwitch.query.filter_by(swid = switchlist[len(switchlist)-1]).first()
        dstswitch = NetworkSwitch.query.filter_by(swid = switchlist[len(switchlist)-2]).first()
        extport = srcswitch.links.filter_by(dstswitch_id = dstswitch.id).first().srcswitch_port
        
        swflow = 'table=1, priority=100,dl_vlan={}, dl_dst={}, actions=output:{}\n'.format(vlan,srcmac,extport)
        flowstrs.append(swflow)
        swflow = 'table=0, priority=99, in_port={}, actions=resubmit(,1)\n'.format(extport)
        flowstrs.append(swflow)
        self.pushflow(switchlist[len(switchlist)-1],flowstrs)
        self.BroadcastIntPortList['s2'].append(1)
        if extport not in self.BroadcastExtPortList[switchlist[len(switchlist)-1]]:
            self.BroadcastExtPortList[switchlist[len(switchlist)-1]].append(extport)
            print 'Ext port list for switch {} is {}'.format(switchlist[len(switchlist)-1],self.BroadcastExtPortList[switchlist[len(switchlist)-1]])
        self.broadcastFlows(switchlist[len(switchlist)-1],101,vlan,True)

    def createAndAddIntermediateFlows(self,switchlist,srcmac,dstmac,vlan):
        for i in range(1,len(switchlist) - 1):
            flowstrs = []
            srcswitch = NetworkSwitch.query.filter_by(swid = switchlist[i]).first()
            prevswitch = NetworkSwitch.query.filter_by(swid = switchlist[i-1]).first()
            nxtswitch = NetworkSwitch.query.filter_by(swid = switchlist[i+1]).first()
            prevport = srcswitch.links.filter_by(dstswitch_id = prevswitch.id).first().srcswitch_port
            nxtport = srcswitch.links.filter_by(dstswitch_id = nxtswitch.id).first().srcswitch_port
        
            swflow = 'table=0, priority=99,in_port={}, actions=resubmit(,1)\n'.format(prevport)
            flowstrs.append(swflow)
            swflow = 'table=1, priority=100, dl_vlan={}, dl_dst={}, actions=output:{}\n'.format(vlan,dstmac,nxtport)
            flowstrs.append(swflow)

            swflow = 'table=0, priority=99,in_port={}, actions=resubmit(,1)\n'.format(nxtport)
            flowstrs.append(swflow)
            swflow = 'table=1, priority=100, dl_vlan={}, dl_dst={}, actions=output:{}\n'.format(vlan,srcmac,prevport)
            flowstrs.append(swflow)
        
            self.pushflow(switchlist[i],flowstrs)
            if prevport not in self.BroadcastExtPortList[switchlist[i]]:
                self.BroadcastExtPortList[switchlist[i]].append(prevport)
            if nxtport not in self.BroadcastExtPortList[switchlist[i]]:
                self.BroadcastExtPortList[switchlist[i]].append(nxtport)
            self.broadcastFlows(switchlist[i],101,vlan,True)


    def addMultiSwitchFlows(self, switchlist, srcmac, dstmac, vlan):
        self.createAndAddSwitchFlows(switchlist,srcmac,dstmac, vlan)
        self.createAndAddIntermediateFlows(switchlist,srcmac,dstmac, vlan)

'''
    def pushflows(sw2flows):
        for sw in sw2flows.keys():
            pushflow(sw, sw2flows[sw])
'''
'''
            if len(self.BroadcastIntPortList[switch]) == 1:
                portlist = ''
                for port in self.BroadcastExtPortList[switch]:
                    if port is not None:
                        portlist += str(port)
                        portlist += ','
                swflow = 'table=1, priority={}, dl_vlan={}, dl_dst=ff:ff:ff:ff:ff:ff, actions=output:{}\n'.format(priority,vlan,portlist)
                flowstrs.append(swflow)
'''

