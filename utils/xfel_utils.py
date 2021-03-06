'''
functions common to fel decks
'''

import scipy.special as sf
import scipy.integrate as integrate
from numpy.polynomial.chebyshev import *
from numpy import *
import numpy as np

from copy import copy, deepcopy
import os, socket, errno, time

from ocelot import *
from ocelot.optics.utils import *
from ocelot.utils.launcher import *
from ocelot.rad.undulator_params import *
from ocelot.rad.fel import *
from ocelot.adaptors.genesis import *
from pylab import *

params = {'backend': 'ps', 'axes.labelsize': 18, 'font.size': 16, 'legend.fontsize': 24, 'xtick.labelsize': 32,  'ytick.labelsize': 32, 'text.usetex': True}
# params = {'backend': 'ps', 'axes.labelsize': 18, 'text.fontsize': 16, 'legend.fontsize': 24, 'xtick.labelsize': 32,  'ytick.labelsize': 32, 'text.usetex': True}
rcParams.update(params)
rc('text', usetex=True) # required to have greek fonts on redhat

def detune_k(lat, sig):
    lat2 = deepcopy(lat)
    n = 0
    for i in xrange(len(lat2.sequence)):
        print lat2.sequence[i].__class__
        if lat2.sequence[i].__class__ == Undulator:
            lat2.sequence[i] = deepcopy(lat.sequence[i]) 
            lat2.sequence[i].Kx = lat2.sequence[i].Kx * (1 + np.random.randn() * sig)
            n += 1

    return lat2

def detune_E(inp, beam, sig):
    # energy modulation
    inp.gamma0 = (beam.E + np.random.randn() * sig) / 0.000510998
    beam.emit_x = beam.emit_xn / inp.gamma0
    beam.emit_y = beam.emit_yn / inp.gamma0
    inp.rxbeam = np.sqrt (beam.emit_x * beam.beta_x )
    inp.rybeam = np.sqrt (beam.emit_y * beam.beta_y )


def taper(lat, k):
    lat2 = deepcopy(lat)
    n = 0
    for i in xrange(len(lat2.sequence)):
        if lat2.sequence[i].__class__ == Undulator:
            #print lat2.sequence[i].id, lat2.sequence[i].Kx
            lat2.sequence[i] = deepcopy(lat.sequence[i]) 
            ##MOD BY GG. #lat2.sequence[i].Kx = lat2.sequence[i].Kx * k(n+1)
            lat2.sequence[i].Kx = k(n+1)#/np.sqrt(0.5) ##MOD BY GG.
            n += 1

    return lat2



def rematch(beta_mean, l_fodo, qdh, lat, extra_fodo, beam, qf, qd):
    
    '''
    requires l_fodo to be defined in the lattice
    '''
    
    k, betaMin, betaMax, __ = fodo_parameters(betaXmean=beta_mean, L=l_fodo, verbose = True)
    
    k1 = k[0] / qdh.l
    
    tw0 = Twiss(beam)
    
    print('before rematching k=%f %f   beta=%f %f alpha=%f %f' % (qf.k1, qd.k1, tw0.beta_x, tw0.beta_y, tw0.alpha_x, tw0.alpha_y))

        
    extra = MagneticLattice(extra_fodo)
    tws=twiss(extra, tw0)
    tw2 = tws[-1]
    
    tw2m = Twiss(tw2)
    tw2m.beta_x = betaMin[0]
    tw2m.beta_y = betaMax[0]
    tw2m.alpha_x = 0.0
    tw2m.alpha_y = 0.0
    tw2m.gamma_x = (1 + tw2m.alpha_x * tw2m.alpha_x) / tw2m.beta_x
    tw2m.gamma_y = (1 + tw2m.alpha_y * tw2m.alpha_y) / tw2m.beta_y

    
    #k1 += 0.5
    
    qf.k1 = k1
    qd.k1 = -k1
    qdh.k1 = -k1
    
    lat.update_transfer_maps()
    extra.update_transfer_maps()

    R1 = lattice_transfer_map( extra, beam.E )
    Rinv = np.linalg.inv(R1)
    
    m1 = TransferMap()

    m1.R = lambda e: Rinv

    tw0m = m1.map_x_twiss(tw2m)
    print 'after rematching k=%f %f   beta=%f %f alpha=%f %f' % (qf.k1, qd.k1, tw0m.beta_x, tw0m.beta_y, tw0m.alpha_x, tw0m.alpha_y)

    beam.beta_x, beam.alpha_x = tw0m.beta_x, tw0m.alpha_x
    beam.beta_y, beam.alpha_y = tw0m.beta_y, tw0m.alpha_y

def rematch_beam_lat(beam, lat, extra_fodo, l_fodo, beta_mean):
    
    isquad=find([i.__class__==Quadrupole for i in lat.sequence])
    qd=lat.sequence[isquad[0]]
    qf=lat.sequence[isquad[1]]
    qdh=deepcopy(qd)
    qdh.l/=2
    '''
    requires l_fodo to be defined in the lattice
    '''
    
    k, betaMin, betaMax, __ = fodo_parameters(betaXmean=beta_mean, L=l_fodo, verbose = False)
    
    k1 = k[0] / qdh.l
    
    tw0 = Twiss(beam)
    
    print('before rematching k=%f %f   beta=%f %f alpha=%f %f' % (qf.k1, qd.k1, tw0.beta_x, tw0.beta_y, tw0.alpha_x, tw0.alpha_y))

        
    extra = MagneticLattice(extra_fodo)
    tws=twiss(extra, tw0)
    tw2 = tws[-1]
    
    tw2m = Twiss(tw2)
    tw2m.beta_x = betaMin[0]
    tw2m.beta_y = betaMax[0]
    tw2m.alpha_x = 0.0
    tw2m.alpha_y = 0.0
    tw2m.gamma_x = (1 + tw2m.alpha_x * tw2m.alpha_x) / tw2m.beta_x
    tw2m.gamma_y = (1 + tw2m.alpha_y * tw2m.alpha_y) / tw2m.beta_y

    
    #k1 += 0.5
    
    qf.k1 = k1
    qd.k1 = -k1
    qdh.k1 = -k1
    
    lat.update_transfer_maps()
    extra.update_transfer_maps()

    R1 = lattice_transfer_map( extra, beam.E )
    Rinv = np.linalg.inv(R1)
    
    m1 = TransferMap()

    m1.R = lambda e: Rinv

    tw0m = m1.map_x_twiss(tw2m)
    print 'after rematching k=%f %f   beta=%f %f alpha=%f %f' % (qf.k1, qd.k1, tw0m.beta_x, tw0m.beta_y, tw0m.alpha_x, tw0m.alpha_y)

    beam.beta_x, beam.alpha_x = tw0m.beta_x, tw0m.alpha_x
    beam.beta_y, beam.alpha_y = tw0m.beta_y, tw0m.alpha_y
    

def run(inp, launcher,readall=False,dfl_slipage_incl=True,assembly_ver='sys'):
    # inp               - GenesisInput() object with genesis input parameters
    # launcher          - MpiLauncher() object obtained via get_genesis_launcher() function
    # readall           - Parameter to read and calculate all _slice_ values from the output. 
    # dfl_slipage_incl  - whether to dedicate time in order to keep the dfl slices, slipped out of the simulation window. if zero, reduces assembly time by ~30%
    # assembly_ver      - version of the assembly script: 'sys' - system based, 'pyt' - python based

    # create experimental directory
    try:
        os.makedirs(inp.run_dir)
    except OSError as exc: 
        if exc.errno == errno.EEXIST and os.path.isdir(inp.run_dir):
            pass
        else: raise
    
    # create and fill necessary input files
    open(inp.run_dir + '/lattice.inp','w').write( inp.lattice_str )
    open(inp.run_dir + '/tmp.cmd','w').write("tmp.gen\n")
    open(inp.run_dir + '/tmp.gen','w').write(inp.input())   
    #print ('    before writing /tmp.beam')
    #print inp.beamfile
    if inp.beamfile != None:
        print ('    writing /tmp.beam')
        open(inp.run_dir + '/tmp.beam','w').write(inp.beam_file_str)
    
    out_file = inp.run_dir + '/run.' + str(inp.runid) + '.gout'
    os.system('rm -rf ' + out_file + '.dfl') # to make sure field file is not attached to old one
    os.system('rm -rf ' + out_file + '.dpa') # to make sure particle file is not attached to old one

    launcher.dir = inp.run_dir
    launcher.prepare()
    
    # RUNNING GENESIS ###
    launcher.launch() ###
    # RUNNING GENESIS ###
    
    # genesis output slices assembly
    print (' ')
    print ('    assembling slices')
    assembly_time = time.time()
    
    if assembly_ver=='sys':
    
        print ('      assembling *.out file')
        start_time = time.time()
        os.system('cat ' + out_file +'.slice* >> '+ out_file)
        print ('        done in %.2f seconds' % (time.time() - start_time))
        print ('      assembling *.dfl file')
        start_time = time.time()
        if dfl_slipage_incl:
            os.system('cat ' + out_file+'.dfl.slice*  >> ' + out_file+'.dfl.tmp')
            #bytes=os.path.getsize(out_file +'.dfl.tmp')
            command='dd if=' + out_file +'.dfl.tmp of='+ out_file +'.dfl conv=notrunc conv=notrunc 2>/dev/null' # obs='+str(bytes)+' skip=1
            os.system(command)
        else:
            os.system('cat ' + out_file+'.dfl.slice*  > ' + out_file+'.dfl')
        print ('        done in %.2f seconds' % (time.time() - start_time))
        print ('      assembling *.dpa file')
        start_time = time.time()
        os.system('cat ' + out_file +'.dpa.slice* >> ' + out_file+'.dpa')
        print ('        done in %.2f seconds' % (time.time() - start_time))
        print ('      removing temporary files')
    
    elif assembly_ver=='pyt':
        import glob
        ram=1
        
        print ('      assembling *.out file')
        start_time = time.time()
        assemble(out_file,ram=ram)
        print ('        done in %.2f seconds' % (time.time() - start_time))
    
        print ('      assembling *.dfl file')
        start_time = time.time()
        assemble(out_file+'.dfl',tailappend=1,ram=ram)
        print ('        done in %.2f seconds' % (time.time() - start_time))
        
        print ('      assembling *.dpa file')
        start_time = time.time()
        assemble(out_file+'.dpa',ram=ram)
        print ('        done in %.2f seconds' % (time.time() - start_time))
    
    # start_time = time.time()
    os.system('rm ' + out_file +'.slice* 2>/dev/null')
    os.system('rm ' + out_file +'.dfl.slice* 2>/dev/null')
    os.system('rm ' + out_file +'.dfl.tmp 2>/dev/null')
    os.system('rm ' + out_file +'.dpa.slice* 2>/dev/null')
    # print ('        done in %.2f seconds' % (time.time() - start_time))
    print ('      total time %.2f seconds' % (time.time() - assembly_time))
    
    g = readGenesisOutput(out_file,readall=readall)
    
    return g

    
def assemble(out_file,binary=1,remove=1,tailappend=0,ram=1):
    import glob, sys
    try:
        if tailappend:
            os.rename(out_file,out_file+'.slice999999')
        
        fins=glob.glob(out_file +'.slice*')
        fins.sort()
        
        #if binary:
        fout = file(out_file,'ab')
        #else:
        #    fout = file(out_file,'a')
        N=len(fins)
        if ram==1:
            idata=''
            data=''
            print('        reading '+str(N)+' slices to RAM...')
            index=10
            for i, n in enumerate(fins):
                # if i/N>=index:
                    # sys.stdout.write(str(index)+'%.')
                    # index +=10
                fin = file(n,'rb')
                while True:
                    idata=fin.read(65536)
                    if not idata:
                        break
                    else:
                        data+=idata
            print('        writing...')
            fout.write(data)
            try:
                fin.close()
            except:
                pass
            
            if remove:
                os.system('rm ' + out_file +'.slice* 2>/dev/null')
                # os.remove(fins)
        else:
            for i, n in enumerate(fins):
                # if i/N>=index:
                    # sys.stdout.write(str(index)+'%.')
                    # index +=10
                fin = file(n,'rb')
                while True:
                    data = fin.read(65536)
                    if not data:
                        break
                    fout.write(data)
                fin.close()
                if remove:
                    os.remove(fin.name)
        
        fout.close()
    except:
        print('        could not assemble '+out_file)
    
    
'''
#### 12.05.2016 MODIFIED BY GG FOR MAXWELL####
'''
def get_genesis_launcher(launcher_program=''):
    host = socket.gethostname()

    launcher = MpiLauncher()
    if launcher_program!='':
        launcher.program=launcher_program
    else:

        if host.startswith('kolmogorov'):
            launcher.program = '/home/iagapov/workspace/xcode/codes/genesis/genesis < tmp.cmd | tee log'
        if host.startswith('max'):
            launcher.program = '/data/netapp/xfel/products/genesis/genesis < tmp.cmd | tee log'
        launcher.mpiParameters ='-x PATH -x MPI_PYTHON_SITEARCH -x PYTHONPATH' #added -n
    #launcher.nproc = nproc
    return launcher

def get_data_dir():
    host = socket.gethostname()
        
    if host.startswith('it-hpc'):
        return '/data/netapp/xfel/iagapov/xcode_data/'
    return '/tmp/'

def create_exp_dir(exp_dir, run_ids):
    for run_id in run_ids:

        try:
            run_dir = exp_dir + 'run_' + str(run_id)
            os.makedirs(run_dir)
        except OSError as exc: 
            if exc.errno == errno.EEXIST and os.path.isdir(run_dir):
                pass
            else: raise

def checkout_run(run_dir, run_id, prefix1, prefix2, save=True):
    print ('    checking out run from '+prefix1+'.gout to '+prefix2+'.gout')
    old_file = run_dir + '/run.' +str(run_id) + prefix1 + '.gout'
    new_file = run_dir + '/run.' +str(run_id) + prefix2 + '.gout'

    if save:
        os.system('cp ' + old_file + ' ' + new_file )
        os.system('cp ' + old_file + '.dfl ' + new_file + '.dfl 2>/dev/null') # 2>/dev/null to supress error messages if no such file
        os.system('cp ' + old_file + '.dpa ' + new_file + '.dpa 2>/dev/null') 
        os.system('cp ' + old_file + '.beam ' + new_file + '.beam 2>/dev/null') 
        os.system('cp '+run_dir+'/tmp.gen'+' '+run_dir+'/geninp.'+str(run_id)+prefix2+'.inp 2>/dev/null')
        os.system('cp '+run_dir+'/lattice.inp'+' '+run_dir+'/lattice.'+str(run_id)+prefix2+'.inp 2>/dev/null')
    else:
        os.system('mv ' + old_file + ' ' + new_file )
        os.system('mv ' + old_file + '.dfl ' + new_file + '.dfl 2>/dev/null') # 2>/dev/null to supress error messages if no such file
        os.system('mv ' + old_file + '.dpa ' + new_file + '.dpa 2>/dev/null') 
        os.system('mv ' + old_file + '.beam ' + new_file + '.beam 2>/dev/null')
        os.system('mv '+run_dir+'/tmp.gen'+' '+run_dir+'/geninp.'+str(run_id)+prefix2+'.inp 2>/dev/null')
        os.system('mv '+run_dir+'/lattice.inp'+' '+run_dir+'/lattice.'+str(run_id)+prefix2+'.inp 2>/dev/null')
    # os.system('rm ' + run_dir + '/run.' +str(run_id) + '.gout*')



def show_output(g, show_field = False, show_slice=0):

    print 'plotting slice', show_slice

    h = 4.135667516e-15
    c = 299792458.0
    xrms = np.array(g.sliceValues[g.sliceValues.keys()[show_slice]]['xrms'])
    yrms = np.array(g.sliceValues[g.sliceValues.keys()[show_slice]]['yrms'])
        
    f = plt.figure()
    f.add_subplot(131), plt.plot(g.z, xrms, lw=3), plt.plot(g.z, yrms, lw=3), plt.grid(True)
    f.add_subplot(132), plt.plot(g.z, g.power_z, lw=3), plt.grid(True)
    t = 1.0e+15 * float(g('zsep')) * float(g('xlamds')) * np.arange(0,len(g.I)) / c

    f.add_subplot(133)
    plt.plot(g.t,g.power_int, lw=3)
    plt.plot(t,g.I * np.max(g.power_int) / np.max(g.I), lw=3)
    plt.grid(True)
    
    npoints = g('ncar')
    zstop = g('zstop')
    delz = g('delz')
    xlamd = g('xlamd')
    xlamds = g('xlamds')
    nslice = g('nslice')
    zsep = g('zsep')
    dgrid = g('dgrid')
    
    smax = nslice * zsep * xlamds   
                 
    print 'wavelength ', xlamds
    
    if show_field:
        #from mpi4py import MPI
        
        #comm = MPI.COMM_WORLD
        #slices = readRadiationFile_mpi(comm=comm, fileName=file+'.dfl', npoints=npoints)
        slices = readRadiationFile(fileName= g.path + '.dfl', npoints=npoints)
        print 'slices:', slices.shape
    
        E = np.zeros_like(slices[0,:,:])
        for i in xrange(slices.shape[0]): E += np.multiply(slices[i,:,:], slices[i,:,:].conjugate())
    
        
        fig = plt.figure()
        fig.add_subplot(131)
        m = plt.imshow(abs(E),cmap='YlOrRd')
        z = abs(slices[100,:,:])

        fig.add_subplot(132)
        P = np.zeros_like(slices[:,0,0])
        for i in xrange(len(P)):
            s = sum( np.abs(np.multiply(slices[i,:,:], slices[i,:,:])) )
            P[i] = abs(s*s.conjugate()) * (dgrid**2 / npoints )**2  
    
            
        t = 1.0e+15 * float(g('zsep')) * float(g('xlamds')) * np.arange(0,len(P)) / c
        plt.plot(t, P)
        plt.title('Pulse/axis')

        fig.add_subplot(133)
        spec = np.abs(np.fft.fft(slices[:,int(npoints/2),int(npoints/2)]))**2
        freq_ev = h * fftfreq(len(spec), d=zsep * xlamds / c) 
        plt.plot(freq_ev, spec)
        plt.title('Spectrum/axis')



'''
putting arbitrarily many plots on single figure
'''
def show_plots(displays, fig):
    n1 = (len(displays) -1 )/2 + 1
    n2 = (len(displays) -1) / n1 +1
    #print n1, n2
    fmt = str(n1)+ str(n2)
    print fmt
    
    for i in xrange(len(displays)):
        ax = fig.add_subplot(fmt + str(i+1))
        ax.grid(True)
        for f in displays[i].data:
            x,y = f(x = np.linspace(-10, 10, 100))
            ax.plot(x, y, '.')

    show()

class Display:
    def __init__(self, data=lambda x: (x, 0*x) , xlabel='',ylabel=''):
        self.data = (data,)
        self.xlabel = xlabel
        self.ylabel = ylabel



def plot_beam(fig, beam):
    
    if mean(beam.x)==0 and mean(beam.y)==0 and mean(beam.px)==0 and mean(beam.py)==0:
        plot_xy=0
    else:
        plot_xy=1
        
    ax = fig.add_subplot(2+plot_xy,2,1) 
    plt.grid(True)
    ax.set_xlabel(r'$\mu m$')
    p1,= plt.plot(1.e6 * np.array(beam.z),beam.I,'r',lw=3)
    plt.plot(1.e6 * beam.z[beam.idx_max],beam.I[beam.idx_max],'bs')
    
    ax = ax.twinx()
    
    p2,= plt.plot(1.e6 * np.array(beam.z),1.e-3 * np.array(beam.eloss),'g',lw=3)
    
    ax.legend([p1, p2],['I [A]','Wake [KV/m]'])
    #ax.set_xlim([np.amin(beam.z),np.amax(beam.x)])
    ax = fig.add_subplot(2+plot_xy,2,2) 
    plt.grid(True)
    ax.set_xlabel(r'$\mu m$')
    #p1,= plt.plot(1.e6 * np.array(beam.z),1.e-3 * np.array(beam.eloss),'r',lw=3)
    p1, = plt.plot(1.e6 * np.array(beam.z),beam.g0,'r',lw=3)
    ax = ax.twinx()
    p2, = plt.plot(1.e6 * np.array(beam.z),beam.dg,'g',lw=3)

    ax.legend([p1,p2],[r'$\gamma$',r'$\delta \gamma$'])
    
    ax = fig.add_subplot(2+plot_xy,2,3) 
    plt.grid(True)
    ax.set_xlabel(r'$\mu m$')
    p1, = plt.plot(1.e6 * np.array(beam.z),beam.ex, 'r', lw=3)
    p2, = plt.plot(1.e6 * np.array(beam.z),beam.ey, 'g', lw=3)
    plt.plot(1.e6 * beam.z[beam.idx_max],beam.ex[beam.idx_max], 'bs')
    
    ax.legend([p1,p2],[r'$\varepsilon_x$',r'$\varepsilon_y$'])
    #ax3.legend([p3,p4],[r'$\varepsilon_x$',r'$\varepsilon_y$'])
    
    
    ax = fig.add_subplot(2+plot_xy,2,4)
    plt.grid(True)
    ax.set_xlabel(r'$\mu m$')
    p1, = plt.plot(1.e6 * np.array(beam.z),beam.betax, 'r', lw=3)
    p2, = plt.plot(1.e6 * np.array(beam.z),beam.betay, 'g', lw=3)
    plt.plot(1.e6 * beam.z[beam.idx_max],beam.betax[beam.idx_max], 'bs')
    
    ax.legend([p1,p2],[r'$\beta_x$',r'$\beta_y$'])

    if plot_xy:

        ax = fig.add_subplot(3,2,5)
        plt.grid(True)
        ax.set_xlabel(r'$\mu m$')
        p1, = plt.plot(1.e6 * np.array(beam.z),1.e6 * np.array(beam.x), 'r', lw=3)
        p2, = plt.plot(1.e6 * np.array(beam.z),1.e6 * np.array(beam.y), 'g', lw=3)
        
        ax.legend([p1,p2],[r'$x [\mu m]$',r'$y [\mu m]$'])

        ax = fig.add_subplot(3,2,6)
        plt.grid(True)
        ax.set_xlabel(r'$\mu m$')
        p1, = plt.plot(1.e6 * np.array(beam.z),1.e6 * np.array(beam.px), 'r', lw=3)
        p2, = plt.plot(1.e6 * np.array(beam.z),1.e6 * np.array(beam.py), 'g', lw=3)
        
        ax.legend([p1,p2],[r'$p_x [\mu rad]$',r'$p_y [\mu rad]$'])

def plot_beam_2(fig, beam, iplot=0):
    
    ax = fig.add_subplot(111) 
    plt.grid(True)
    
    if iplot == 0:
    
        ax.set_xlabel(r'$\mu m$')
        ax.set_ylabel('A')
        p1,= plt.plot(1.e6 * np.array(beam.z),beam.I,'r',lw=3)
        #plt.plot(1.e6 * beam.z[beam.idx_max],beam.I[beam.idx_max],'bs')
        
        ax = ax.twinx()
        ax.set_ylabel('KV/m')
        
        p2,= plt.plot(1.e6 * np.array(beam.z),1.e-3 * np.array(beam.eloss),'g',lw=3)
        
        ax.legend([p1, p2],['I',r'$E_{wake}$'])

    if iplot == 1:
    
        ax.set_xlabel(r'$\mu m$')
        #p1,= plt.plot(1.e6 * np.array(beam.z),1.e-3 * np.array(beam.eloss),'r',lw=3)
        p1, = plt.plot(1.e6 * np.array(beam.z),beam.g0,'r',lw=3)
        ax = ax.twinx()
        p2, = plt.plot(1.e6 * np.array(beam.z),beam.dg,'g',lw=3)
    
        ax.legend([p1,p2],[r'$\gamma$',r'$\delta \gamma$'])
    
    if iplot == 2:

        ax.set_xlabel(r'$\mu m$')
        ax.set_ylabel(r'$mm \cdot mrad$')
        p1, = plt.plot(1.e6 * np.array(beam.z),1.e6*np.array(beam.ex), 'r', lw=3)
        p2, = plt.plot(1.e6 * np.array(beam.z),1.e6*np.array(beam.ey), 'g', lw=3)
        #plt.plot(1.e6 * beam.z[beam.idx_max],beam.ex[beam.idx_max], 'bs')
        
        ax.legend([p1,p2],[r'$\varepsilon_x$',r'$\varepsilon_y$'])
        #ax3.legend([p3,p4],[r'$\varepsilon_x$',r'$\varepsilon_y$'])
    
    if iplot == 3:
    
        ax.set_xlabel(r'$\mu m$')
        ax.set_ylabel(r'$m$')
        p1, = plt.plot(1.e6 * np.array(beam.z),beam.betax, 'r', lw=3)
        p2, = plt.plot(1.e6 * np.array(beam.z),beam.betay, 'g', lw=3)
        #plt.plot(1.e6 * beam.z[beam.idx_max],beam.betax[beam.idx_max], 'bs')
        
        ax.legend([p1,p2],[r'$\beta_x$',r'$\beta_y$'])

'''
configurable to e.g. semi-empirical models
'''
class FelSimulator(object):
    
    def __init__(self):
        self.engine = 'genesis'
    
    def run(self):
        if self.engine == 'test_1d':
            w1 = read_signal(file_name=self.input, npad = self.npad , E_ref = self.E_ev)
            return w1, None
        if self.engine == 'test_3d':
            ''' produced  sliced field '''
            w1 = read_signal(file_name=self.input, npad = self.npad , E_ref = self.E_ev)
            s3d = Signal3D()
            s3d.fs = [w1, deepcopy(w1), deepcopy(w1), deepcopy(w1)]
            s3d.mesh_size = (2,2)            
            return s3d, None
        if self.engine == 'test_genesis':
            ''' read test sliced field '''
            g = readGenesisOutput(self.input)
            print 'read sliced field ', g('ncar'), g.nSlices
            slices = readRadiationFile(fileName=self.input + '.dfl', npoints=g('ncar'))            
            s3d = Signal3D()
            s3d.slices = slices
            s3d.mesh_size = (int(g('ncar')),int(g('ncar'))) 
            s3d.g = g           
            return s3d, None

def background(command):
    '''
    start command as background process
    the argument shohuld preferably be a string in triple quotes '
    '''
    import subprocess
    imports='from ocelot.gui.genesis_plot import *; from ocelot.adaptors.genesis import *; from ocelot.utils.xfel_utils import *; '
    subprocess.Popen(["python","-c",imports + command])
