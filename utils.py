from pylab import *
import numpy as np

def xify(p,params = ['n','xcab','xcar','cbrown','xcw','xcm','xala','bsoil','psoil','hspot','xlai']):
  '''
  Fix the state key names by putting x on where appropriate
  '''
  retval = {}
  for i in p.keys():
    if 'x' + i in params:
      retval['x' + i] = p[i]
    else:
      retval[i] = p[i]
  return retval

def invtransform(params,total=False,\
        logvals = {'ala': 90., 'lai':-2.0, 'cab':-100., 'car':-100., 'cw':-1/50., 'cm':-1./100}):
  '''
  Parameters:

    params : parameter dictionary

  Options:

    logvals : log scaling values
    total   : for leaf quantities, multiply by LAI
  '''
  if total:
    logvals['cab'] *= 2.
    logvals['car'] *= 2.
    logvals['cw'] *= 2.
    logvals['cm'] *= 2
    logvals['cbrown'] = 15.

  retval = {}
  for i in xify(params).keys():
    if i[0] != 'x':
      retval[i] = params[i]
    else:
      rest = i[1:]
      try:
        if logvals[rest] < 0:
          retval[rest] = logvals[rest] * np.log(params[i])
        else:
          retval[rest] = params[i] * logvals[rest]
      except:
        retval[rest] = params[i]
  return retval

def transform(params,total=False,\
    logvals = {'ala': 90., 'lai':-2.0, 'cab':-100., 'car':-100., 'cw':-1/50., 'cm':-1./100}):

  '''
  Parameters:

    params : parameter dictionary

  Options:

    logvals : log scaling values
    total   : for leaf quantities, multiply by LAI
  '''
  if total:
    logvals['cab'] *= 2.
    logvals['car'] *= 2.
    logvals['cw'] *= 2.
    logvals['cm'] *= 2
    logvals['cbrown'] = 15.

  retval = {}
  for i in xify(params).keys():
    if i[0] != 'x':
      retval[i] = params[i]
    else:
      rest = i[1:]
      try:
        if logvals[rest] < 0:
          retval[i] = np.exp(params[rest] / logvals[rest])
        else:
          retval[i] = params[rest] / logvals[rest]
      except:
        retval[i] = params[i]
  return retval

def limits(total=False):
  '''
  Set limits for parameters

  Options:
  
    total : True then set this for *total* canopt chlorophyll etc (i.e. multiply by LAI)
  '''
  params = ['n','xcab','xcar','cbrown','xcw','xcm','xala','bsoil','psoil','hspot','xlai']
  pmin = {}
  pmax = {}
  # set up defaults
  for i in params:
    pmin[i] = 0.001
    pmax[i] = 1. - 0.001
  if total:
    laiMult = 15.
  else:
    laiMult = 1.0
  # now specific limits
  # These from Feret et al.
  pmin['xlai'] = transform({'lai':15.})['xlai']
  pmin['xcab'] = transform({'cab':0.2})['xcab']
  pmax['xcab'] = transform({'cab':76.8*laiMult})['xcab']
  pmin['xcar'] = transform({'car':25.3*laiMult})['xcar']
  pmax['xcar'] = transform({'car':0.})['xcar']
  pmin['cbrown'] = 1.*laiMult
  pmax['cbrown'] = 0.
  pmin['xcm'] = transform({'cm':0.0017})['xcm']
  pmax['xcm'] = transform({'cm':0.0331*laiMult})['xcm']
  pmin['xcw'] = transform({'cw':0.0043})['xcw']
  pmax['xcw'] = transform({'cw':0.0713*laiMult})['xcw']

  pmin['n'] = 0.8
  pmax['n'] = 2.5
  pmin['bsoil'] = 0.0
  pmax['bsoil'] = 2.0
  pmin['psoil'] = 0.0
  pmax['psoil'] = 1.0
  pmin['xala'] = transform({'ala':90.})['xala']
  pmax['xala'] = transform({'ala':0.})['xala']
  for i in params:
    if pmin[i] > pmax[i]:
      tmp = pmin[i]
      pmin[i] = pmax[i]
      pmax[i] = tmp
  return (pmin,pmax)


def fixnan(x):
  '''
  the RT model sometimes fails so we interpolate over nan

  This method replaces the nans in the vector x by their interpolated values
  '''
  for i in xrange(x.shape[0]):
    sample = x[i]
    ww = np.where(np.isnan(sample))
    nww = np.where(~np.isnan(sample))
    sample[ww] = np.interp(ww[0],nww[0],sample[nww])
    x[i] = sample
  return x

def addDict(input,new):
  '''
  add dictionary items
  '''
  for i in new.keys():
    try:
      input[i] = np.hstack((np.atleast_1d(input[i]),np.atleast_1d(new[i])))
    except:
      input[i] = np.array([new[i]]).flatten()
  return input

def unpack(params):
  '''
  Input a dictionary and output keys and array
  '''
  inputs = []
  keys = np.sort(params.keys())
  for i,k in enumerate(keys):
    inputs.append(params[k])
  inputs=np.array(inputs).T
  return inputs,keys

def pack(inputs,keys):
  '''
  Input keys and array and output dict
  '''
  params = {}
  for i,k in enumerate(keys):
    params[k] = inputs[i]
  return params

def sampler(pmin,pmax):
  '''
  Random sample
  '''
  params = {}
  for i in pmin.keys():
    params.update(invtransform({i:pmin[i] + np.random.rand()*(pmax[i]-pmin[i])}))
  return params


def samples(n=2):
  '''
  Random samples over parameter space
  '''
  (pmin,pmax) = limits()
  s = {}
  for i in xrange(n):
    s = addDict(s,sampler(pmin,pmax))
  return s


def reconstruct(gps,SB,inputs):
  '''
  spectral reconstruction from GPs and spectral basis functions
  '''
  fwd = 0
  inputs = np.atleast_2d(np.array(inputs))
  for i in xrange(SB.shape[0]):
    pred_mu, pred_var, grad  = gps[i].predict(inputs)
    fwd += np.matrix(pred_mu).T * np.matrix(SB[i])
  return np.array(fwd)

def reconstructD(gps,SB,inputs):
  '''
  spectral reconstruction from GPs and spectral basis functions
  '''
  fwd = 0
  inputs = np.atleast_2d(np.array(inputs))
  deriv = np.zeros((inputs.shape[1],SB[0].shape[0]))
  derivt = np.zeros((inputs.shape[1],SB[0].shape[0]))

  for i in xrange(SB.shape[0]):
    pred_mu, pred_var, grad  = gps[i].predict(inputs)
    fwd += np.matrix(pred_mu).T * np.matrix(SB[i])
    deriv += np.matrix(grad).T * np.matrix(SB[i])
  # check code , but its the same
  #for j in xrange(inputs.shape[1]):
  #  for i in xrange(SB.shape[0]):
  #    pred_mu, pred_var, grad  = gps[i].predict(inputs)
  #    derivt[j,:] += grad[:,j] * SB[i]
  return np.array(fwd)[0],deriv


def brdfModel(s,vza,sza,raa,bandpass=None):
  '''
  Run the full BRDF model for parameters in s

  Parameters:
    s   : dictionary of model parameters (state)
    vza : view zenith angle (degrees) 
          float or float array of the same size as the number of
          entries in each dictionary item
    sza : solar zenith angle (degrees) 
          float or float array of the same size as the number of
          entries in each dictionary item
    raa : relative azimuth angle (degrees) 
          float or float array of the same size as the number of
          entries in each dictionary item

  Options:
    bandpass : set of bandpass functions
  '''
  from prosail_fortran import run_prosail 
  brdf = []
  wavelength = np.arange(400,2501).astype(float)
  for i in xrange(len(s['n'])):
    try:
      brf = run_prosail(s['n'][i],s['cab'][i],s['car'][i],s['cbrown'][i],s['cw'][i],s['cm'][i],\
                s['lai'][i],s['ala'][i],0.0,s['bsoil'][i],s['psoil'][i],s['hspot'][i],\
                vza[i],sza[i],raa[i],2)
    except:
      brf = run_prosail(s['n'][i],s['cab'][i],s['car'][i],s['cbrown'][i],s['cw'][i],s['cm'][i],\
                s['lai'][i],s['ala'][i],0.0,s['bsoil'][i],s['psoil'][i],s['hspot'][i],\
                vza,sza,raa,2)
    if bandpass:
      brf = bandpass * brf
    brdf.append(brf)
  if bandpass:
    wavelength = bandpass * wavelength    
  return (vza,sza,raa),transform(s),fixnan(np.array(brdf)),wavelength


def lut(n=2,vza=0.,sza=45.,raa=0.,brdf=None,bands=None):
  '''
  Generate a random LUT for given viewing and illumination geometry
  '''
  # get the parameter limits
  (pmin,pmax) = limits()

  # generate some random samples over the parameter space
  s = samples(n=n)
  return brdfModel(s,vza,sza,raa)


