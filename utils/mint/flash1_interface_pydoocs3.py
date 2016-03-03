'''
machine interface
includes online optimizer, response measurement and other stuff
'''
try:
    # in server "doocsdev12" set environment
    #  $ export PYTHONPATH=/home/ttflinac/user/python-2.7/Debian/
    import pydoocs
except:
    print ('error importing doocs library')
    
import re
from pylab import *
from ocelot.utils.mint.machine_setup import *


class SaveOptParams:
    def __init__(self, mi, dp, lat=None):
        self.mi = mi
        self.dp = dp
        self.hlmint = None
        if lat != None:
            self.hlmint = HighLevelInterface(lat, mi, dp)


    def save(self, args, time, niter, flag="start"):
        data_base = {}
        data_base["flag"] = flag
        data_base["timestamp"] = time
        data_base["devices"] = args[0]
        data_base["method"] = args[1]
        data_base["maxiter"] = args[2]["maxiter"]
        limits = []
        currents = []
        for dev in data_base["devices"]:
            limits.append(self.dp.get_limits(dev))
            currents.append(self.mi.get_value(dev))
        data_base["limits"] = limits
        data_base["currents"] = currents
        data_base["sase_pos"] = self.mi.get_sase_pos()
        data_base["niter"] = niter
        data_base["sase"] = self.mi.get_sase()
        data_base["sase_slow"] = self.mi.get_sase(detector='gmd_fl1_slow')
        orbit = []
        dict_cav = {}

        if self.hlmint != None:
            orbit = self.hlmint.read_bpms()
            dict_cav = self.hlmint.read_cavs()
        #data_base["orbit"] = orbit
        #data_base["cavs"] = dict_cav
        data_base["wavelength"] = 0
        data_base["charge"] = 0
        data_base["gun_energy"] = self.mi.get_gun_energy()
        print("save action", data_base)


class FLASH1MachineInterface():
    def __init__(self):
        
        self.debug = False
        """
        self.blm_names = ['14L.SMATCH','14R.SMATCH',
                          '1L.UND1', '1R.UND1',
                          '1L.UND2', '1R.UND2', 
                          '1L.UND3', '1R.UND3', 
                          '1L.UND4', '1R.UND4',
                          '1L.UND5', '1R.UND5',
                          '1L.UND6', '1R.UND6',
                          '10SMATCH','3SDUMP']
        """
        self.blm_names = ['1L.UND1', '1R.UND1',
                          '1L.UND2', '1R.UND2',
                          '1L.UND3', '1R.UND3',
                          '1L.UND4', '1R.UND4',
                          '1L.UND5', '1R.UND5',
                          '1L.UND6', '1R.UND6',
                          '10SMATCH','3SDUMP']



    def init_corrector_vals(self, correctors):
        vals = np.zeros(len(correctors))
        for i in range(len(correctors)):
            mag_channel = 'TTF2.MAGNETS/STEERER/' + correctors[i] + '/PS'
            vals[i] = pydoocs.read(mag_channel)["data"]
        return vals

    def get_cavity_info(self, cavs):
        ampls = [0.0]*len(cavs)#np.zeros(len(correctors))
        phases = [0.0]*len(cavs)#np.zeros(len(correctors))
        for i in range(len(cavs)):
            #ampl_channel = 'FLASH.RF/LLRF.CONTROLLER/CTRL.' + cavs[i] + '/SP.AMPL'
            #phase_channel = 'FLASH.RF/LLRF.CONTROLLER/CTRL.' + cavs[i] + '/SP.PHASE'
            ampl_channel = "FLASH.RF/LLRF.CONTROLLER/PVS." + cavs[i] + "/AMPL.SAMPLE"
            phase_channel = "FLASH.RF/LLRF.CONTROLLER/PVS." + cavs[i]+ "/PHASE.SAMPLE"
            ampls[i] = pydoocs.read(ampl_channel)['data']
            phases[i] = pydoocs.read(phase_channel)['data']
            #print cavs[i], ampls[i], phases[i]
        return ampls, phases

    def get_gun_energy(self):
        gun_energy = pydoocs.read("FLASH.RF/LLRF.ENERGYGAIN.ML/GUN/ENERGYGAIN.FLASH1")['data']
        gun_energy = gun_energy*0.001 # MeV -> GeV
        return gun_energy

    def get_bpms_xy(self, bpms):
        X = [0.0]*len(bpms)#np.zeros(len(correctors))
        Y = [0.0]*len(bpms)
        for i in range(len(bpms)):
            mag_channel = 'TTF2.DIAG/ORBIT/' + bpms[i]# + '/PS'
            X[i] = pydoocs.read(mag_channel + "/X.FLASH1")['data']*0.001 # mm -> m
            Y[i] = pydoocs.read(mag_channel + "/Y.FLASH1")['data']*0.001 # mm -> m
        return X, Y

    def get_quads_current(self, quads):
        vals = np.zeros(len(quads))
        for i in range(len(quads)):
            mag_channel = 'TTF2.MAGNETS/QUAD/' + quads[i]# + '/PS'
            vals[i] = pydoocs.read(mag_channel + "/PS")['data']
        return vals

    def get_bends_current(self, bends):
        vals = [0.0]*len(bends)#np.zeros(len(correctors))
        for i in range(len(bends)):
            mag_channel = 'TTF2.MAGNETS/DIPOLE/' + bends[i]# + '/PS'
            vals[i] = pydoocs.read(mag_channel + "/PS")['data']
        return vals

    def get_sext_current(self, sext):
        vals = [0.0]*len(sext)#np.zeros(len(correctors))
        for i in range(len(sext)):
            mag_channel = "TTF2.MAGNETS/SEXT/" + sext[i]
            vals[i] = pydoocs.read(mag_channel + "/PS")['data']
        return vals

    def get_alarms(self):
        alarm_vals = np.zeros(len(self.blm_names))
        for i in range(len(self.blm_names)):
            blm_channel = 'TTF2.DIAG/BLM/'+self.blm_names[i]+'/CH00.TD'
            blm_alarm_ch  = ('TTF2.DIAG/BLM/'+self.blm_names[i]).replace('BLM', 'BLM.ALARM') + '/THRFHI'
            if (self.debug): print('reading alarm channel', blm_alarm_ch)
            alarm_val = pydoocs.read(blm_alarm_ch)['data'] * 1.25e-3 # alarm thr. in Volts
            if (self.debug): print ('alarm:', alarm_val)
            sample = pydoocs.read(blm_channel)['data']
            h = np.array([x[1] for x in sample])

            alarm_vals[i] = np.max( np.abs(h) ) / alarm_val 
            
        return alarm_vals

    def get_sase(self, detector='gmd_default'):
        
        if detector == 'mcp':
            # incorrect
            return pydoocs.read('TTF2.DIAG/MCP.HV/MCP.HV1/HV_CURRENT')['data']
            #return np.abs( np.mean(h) )
        if detector == 'gmd_fl1_slow':
            return pydoocs.read('TTF2.FEL/BKR.FLASH.STATE/BKR.FLASH.STATE/SLOW.INTENSITY' )['data']

        # default 'BKR' gmd
        h = np.array(pydoocs.read('TTF2.FEL/BKR.FLASH.STATE/BKR.FLASH.STATE/ENERGY.CLIP.SPECT')['data'])
        val = np.mean(np.array([x[1] for x in h]))
        return val



    def get_sase_pos(self):

        x1 = pydoocs.read('TTF2.FEL/GMDPOSMON/TUNNEL/IX.POS')['data']
        y1 = pydoocs.read('TTF2.FEL/GMDPOSMON/TUNNEL/IY.POS')['data']

        x2 = pydoocs.read('TTF2.FEL/GMDPOSMON/BDA/IX.POS')['data']
        y2 = pydoocs.read('TTF2.FEL/GMDPOSMON/BDA/IY.POS')['data']
    
        return [ (x1,y1), (x2,y2) ] 

    def get_spectrum(self, f=None, detector='tunnel_default'):

        f_min = 13.0 # spectrum window (nm). TODO: replace with readout
        f_max = 14.0
        
        spec = np.array(pydoocs.read('TTF2.EXP/PBD.PHOTONWL.ML/WAVE_LENGTH/VAL.TD')['data'])
    
        if f == None:
            f = np.linspace(f_min, f_max, len(spec))
    
        return f, spec
 
    def get_value(self, device_name):
        ch = 'TTF2.MAGNETS/STEERER/' + device_name + '/PS.RBV'
        return pydoocs.read(ch)['data']
    
    def set_value(self, device_name, val):
        ch = 'TTF2.MAGNETS/STEERER/' + device_name + '/PS'
        print (ch, val)
        return 0#pydoocs.write(ch, str(val))
 
 
class FLASH1DeviceProperties:
    def __init__(self):
        self.stop_exec = False
        self.save_machine = False
        self.patterns = {}
        self.limits = {}
        self.patterns['launch_steerer'] = re.compile('[HV][0-9]+SMATCH')
        self.limits['launch_steerer'] = [-4,4]
        
        self.patterns['intra_steerer'] = re.compile('H3UND[0-9]')
        self.limits['intra_steerer'] = [-5.0,-2.0]
        
        self.patterns['QF'] = re.compile('Q5UND1.3.5')
        self.limits['QF'] = [1,7]
        
        self.patterns['QD'] = re.compile('Q5UND2.4')
        self.limits['QD'] = [-5,-1]
        
        self.patterns['Q13MATCH'] = re.compile('Q13SMATCH')
        self.limits['Q13MATCH'] = [17.0,39.0]

        self.patterns['Q15MATCH'] = re.compile('Q15SMATCH')
        self.limits['Q15MATCH'] = [-16.0,-2.0]

        self.patterns['H3DBC3'] = re.compile('H3DBC3')
        self.limits['H3DBC3'] = [-0.035, -0.018]

        self.patterns['V3DBC3'] = re.compile('V3DBC3')
        self.limits['V3DBC3'] = [-0.1, 0.10]

        self.patterns['H10ACC7'] = re.compile('H10ACC7')
        self.limits['H10ACC7'] = [0.12, 0.17]

        self.patterns['H10ACC6'] = re.compile('H10ACC6')
        self.limits['H10ACC6'] = [-0.9, -0.4]

        self.patterns['H10ACC5'] = re.compile('H10ACC5')
        self.limits['H10ACC5'] = [0.8, 1.2]

        self.patterns['H10ACC4'] = re.compile('H10ACC4')
        self.limits['H10ACC4'] = [-0.2, 0.1]

        self.patterns['V10ACC7'] = re.compile('V10ACC7')
        self.limits['V10ACC7'] = [-2.6,-1.8]

        self.patterns['V10ACC4'] = re.compile('V10ACC4')
        self.limits['V10ACC4'] = [0.9,1.2]

        self.patterns['V10ACC5'] = re.compile('V10ACC5')
        self.limits['V10ACC5'] = [-0.7,-0.5]


        self.patterns['H8TCOL'] = re.compile('H8TCOL')
        self.limits['H8TCOL'] = [0.04,0.05]

        self.patterns['V8TCOL'] = re.compile('V8TCOL')
        self.limits['V8TCOL'] = [0.033,0.043]
        
        self.patterns['V1ORS'] = re.compile('V1ORS')
        self.limits['V1ORS'] = [0.1, 0.15]

        self.patterns['H5ORS'] = re.compile('H5ORS')
        self.limits['H5ORS'] = [-0.06, -0.01]

        self.patterns['H10ORS'] = re.compile('H10ORS')
        self.limits['H10ORS'] = [-0.2, -0.1]

        self.patterns['V12ORS'] = re.compile('V12ORS')
        self.limits['V12ORS'] = [0.04, 0.15]

    def set_limits(self, dev_name, limits):
        self.patterns[dev_name] = re.compile(dev_name)
        #print(self.patterns[dev_name])
        self.limits[dev_name] = limits
        #print("inside dp set = ", self.patterns[dev_name], self.limits)

    def get_limits(self, device):
        #print(self.limits)
        for k in self.patterns.keys():
            #print('testing', k)
            if self.patterns[k].match(device) != None:
                #print("inside dp get = ", device, self.limits[k])
                return self.limits[k]
        return [-2, 2]

    def get_polarity(self, quads):
        vals = [0.0]*len(quads)#np.zeros(len(correctors))
        for i in range(len(quads)):
            mag_channel = 'TTF2.MAGNETS/QUAD/' + quads[i]# + '/PS'
            vals[i] = pydoocs.read(mag_channel + "/PS.Polarity")['data']
        return vals

    def get_type_magnet(self, quads):
        vals = [0.0]*len(quads)#np.zeros(len(correctors))
        for i in range(len(quads)):
            mag_channel = 'TTF2.MAGNETS/QUAD/' + quads[i]# + '/PS'
            vals[i] = pydoocs.get(mag_channel + "/DEVTYPE")['data']
        return vals

