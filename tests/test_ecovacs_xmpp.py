from re import search

from nose.tools import *

from sucks import *


# There are few tests for the XMPP stuff here because it's relatively complicated to test given
# the library's design and its multithreaded nature and lack of explicit testing support.

def test_wrap_command():
    x = make_ecovacs_xmpp()
    c = str(x._wrap_command(Clean().to_xml(), 'E0000000001234567890@126.ecorobot.net/atom'))
    assert_true(search(r'from="20170101abcdefabcdefa@ecouser.net/abcdef12"', c))
    assert_true(search(r'to="E0000000001234567890@126.ecorobot.net/atom"', c))    
    #Convert to XML to make it easy to see if id was added to ctl
    xml_test = ET.fromstring(c)
    ctl = xml_test.getchildren()[0][0]
    assert_true(ctl.get("id")) #Check that an id was added to ctl    

    #Test if customid is added to ctl
    cwithid = Clean().to_xml()
    cwithid.attrib["id"] = "12345678" #customid 12345678
    c = str(x._wrap_command(cwithid, 'E0000000001234567890@126.ecorobot.net/atom'))    
    #Convert to XML to make it easy to see if id was added to ctl
    xml_test = ET.fromstring(c)
    ctl = xml_test.getchildren()[0][0]
    assert_equals(ctl.get("id"), "12345678") #Check that an id was added to ctl    


def test_getReqID():
    x = make_ecovacs_xmpp()
    rid = x.getReqID("12345678")
    assert_equals(rid, "12345678") #Check returned ID is the same as provided

    rid2 = x.getReqID()
    assert_true(len(rid2) >= 8) #Check returned random ID is at least 8 chars

def test_subscribe_to_ctls():
    response = None

    def save_response(value):
        nonlocal response
        response = value

    x = make_ecovacs_xmpp()

    query = x.make_iq_query()
    query.set_payload(
        ET.fromstring('<query xmlns="com:ctl"><ctl td="CleanReport"> <clean type="auto" /> </ctl></query>'))

    x.subscribe_to_ctls(save_response)
    x._handle_ctl(query)
    assert_dict_equal(response, {'event': 'clean_report', 'type': 'auto'})

    # Clean Ozmo
    response = None
    query = x.make_iq_query()
    query.set_payload(
        ET.fromstring('<query xmlns="com:ctl"><ctl id="72515851" ret="ok"><clean type="auto" speed="standard" st="h" t="0" a="0" s="0" tr=""/></ctl></query>'))

    x._handle_ctl(query)
    assert_dict_equal(response, {'event': 'clean_report', 'type': 'auto', 'speed': 'standard', 'st':'h', 't':'0','a':'0','s':'0', 'tr':'', 'id':'72515851', 'ret':'ok'})

    # Clean Report Ozmo
    response = None
    query = x.make_iq_query()
    query.set_payload(
        ET.fromstring('<query xmlns="com:ctl"><ctl ts="287462755" td="CleanReport"><clean type="auto" speed="standard" st="s" rsn="" a="" l="" sts=""/></ctl></query>'))

    x._handle_ctl(query)
    assert_dict_equal(response, {'event': 'clean_report', 'type': 'auto', 'speed': 'standard', 'st':'s', 'rsn':'', 'a':'', 'l':'', 'sts':'', 'ts':'287462755'})

    # Clean Error Ozmo
    response = None
    query = x.make_iq_query()
    query.set_payload(
        ET.fromstring('<query xmlns="com:ctl"><ctl id="72515851" ret="fail" errno="0"/></query>'))

    x._handle_ctl(query)
    assert_equals(response, None)

    # Charge State Ozmo
    response = None
    query = x.make_iq_query()
    query.set_payload(
        ET.fromstring('<query xmlns="com:ctl"><ctl id="75510041" ret="ok"><charge type="Idle"/></ctl></query>'))
  
    x._handle_ctl(query)
    assert_dict_equal(response, {'event': 'charge_state', 'type': 'idle', 'ret':'ok', 'id':'75510041'})

    # Battery Info Ozmo
    response = None
    query = x.make_iq_query()
    query.set_payload(
        ET.fromstring('<query xmlns="com:ctl"><ctl id="22564403" ret="ok"><battery power="83"/></ctl></query>'))

    x._handle_ctl(query)
    assert_dict_equal(response, {'event': 'battery_info', 'power': '83', 'ret':'ok', 'id':'22564403'})

def test_xml_to_dict():
    x = make_ecovacs_xmpp()

    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl td="CleanReport"> <clean type="auto" /> </ctl>')),
        {'event': 'clean_report', 'type': 'auto'})
    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl td="CleanReport"> <clean type="auto" speed="strong" /> </ctl>')),
        {'event': 'clean_report', 'type': 'auto', 'speed': 'strong'})

    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl td="BatteryInfo"><battery power="095"/></ctl>')),
        {'event': 'battery_info', 'power': '095'})

    assert_dict_equal(
        x._ctl_to_dict(make_ctl('# <ctl td="LifeSpan" type="Brush" val="099" total="365"/>')),
        {'event': 'life_span', 'type': 'brush', 'val': '099', 'total': '365'})
    # set of xml responses without the td attrib
    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl type="DustCaseHeap" val="050" total="365"/>')),
        {'event': 'life_span', 'type': 'dust_case_heap', 'val': '050', 'total': '365'})

    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl ret="ok" errno=""><battery power="099"/></ctl>')),
        {'event': 'battery_info', 'power': '099', 'ret': 'ok', 'errno': ''})

    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl td="LifeSpan" type="DustCaseHeap" val="-050" total="365"/>')),
        {'event': 'life_span', 'type': 'dust_case_heap', 'val': '-050', 'total': '365'})
    
    assert_equals(x._ctl_to_dict(make_ctl('<ctl />')), None)

    assert_equals(x._ctl_to_dict(make_ctl('<ctl ret="ok" errno=""><clean type="stop" speed="strong" st="h" t="" a=""/></ctl>')),
        {'event': 'clean_report', 'type': 'stop', 'speed': 'strong', 'st':'h', 't': '', 'a': '', 'ret':'ok', 'errno': ''})

    assert_dict_equal(
        x._ctl_to_dict(make_ctl('<ctl ret="ok" errno=""><charge type="SlotCharging"/></ctl>')),
        {'event': 'charge_state', 'type': 'slot_charging', 'ret': 'ok', 'errno': ''})

def make_ecovacs_xmpp(bot=None, server_address=None):
    if bot is None:
        bot = {"did": "E0000000001234567890", "class": "126", "nick": "bob", "iotmq": False}    
    return EcoVacsXMPP('20170101abcdefabcdefa', 'ecouser.net', 'abcdef12', 'A1b2C3d4efghijklmNOPQrstuvwxyz12', 'na', bot, server_address=server_address)

def test_xmpp_customaddress():
    x = make_ecovacs_xmpp(server_address="test.xmppserver.com")
    assert_equals(x.server_address, "test.xmppserver.com")

def make_ctl(string):
    return ET.fromstring('<query xmlns="com:ctl">' + string + '</query>')[0]
