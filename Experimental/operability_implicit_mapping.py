# -*- coding: utf-8 -*-
"""
Created on Mon Nov 28 14:31:26 2022

@author: sqd0001
"""
from jax.config import config
from jax import lax, jacfwd, jacrev
from jax.numpy.linalg import pinv
config.update("jax_enable_x64", True)

import jax.numpy as jnp
import numpy as np
from jax.experimental.ode import odeint

from scipy.optimize import root, fsolve
# %% REMOVE THIS BEFORE RELEASE
from DMA_MR_ss import *

# %% Functions
def implicit_map(f_model, 
                 domain_bound, 
                 domain_resolution, 
                 image_init,
                 direction = 'forward', 
                 validation = 'predictor-corrector', 
                 tol_cor = 1e-8, 
                 continuation = 'odeint',
                 derivative = 'jax'):
    '''
    @author: San Dinh

    Parameters
    ----------
    f_model : TYPE
        DESCRIPTION. f_model(Input Vector, Output Vector) = 0
    domain_bound : TYPE
        DESCRIPTION.
    domain_resolution : TYPE
        DESCRIPTION.
    direction : TYPE, optional
        DESCRIPTION. The default is 'forward'.
        'inverse'
    validation : TYPE, optional
        DESCRIPTION. The default is 'predictor-corrector'.
        'predictor'
        'corrector'
    tol_cor : TYPE, optional
        DESCRIPTION. The default is 1e-8.
    continuation : TYPE, optional
        DESCRIPTION. The default is 'odeint'.
        'Explicit RK4'
        'Explicit Huen'
        'Explicit Euler'

    Returns
    -------
    int
        DESCRIPTION.

    '''
    # %% Implicit function theorem
    if direction == 'forward':
        print('Forward Mapping Selected.')
        print('The given domain is recognized as an Available Input Set (AIS).')
        print('The result of this mapping is an Achievable Output Set(AOS)')
        
        F       = lambda i, o : f_model(i,o)
        F_io    = lambda o, i : f_model(i,o)
    elif direction == 'inverse':
        print('Inverse Mapping Selected.')
        print('The given domain is recognized as Desired Output Set (DOS).')
        print('The result of this mapping is an Desired Input Set(DIS)')
        
        F       = lambda i, o : f_model(o, i)
        F_io    = lambda o, i : f_model(o, i)
    else:
        print('Invalid Mapping Selected. Please select the direction to be either "forward" or "inverse"')
    
    dFdi = jacrev(F, 0)
    dFdo = jacrev(F, 1)
    dodi = lambda ii,oo: -pinv(dFdo(ii,oo)) @ dFdi(ii,oo)
    # dodi = lambda ii,oo: -pinv(dFdi(ii,oo)) @ dFdo(ii,oo)
    # dodi = lambda ii,oo: np.array(-dFdo(ii,oo)).squeeze() @ np.array(pinv(dFdi(ii,oo))).squeeze()
    # slack_in = domain_bound[:,0]
    # slack_out = np.array([32.00,32.00])
    # return dodi(np.array([1.0,2.0]), np.array([32.00,32.00]))
    
    # %% Initializing
    sol = root(F_io, image_init,args=domain_bound[:,0])
    
    # %% Pre-alocating the domain set
    numInput = np.prod(domain_resolution)
    nInput = domain_bound.shape[0]
    nOutput = image_init.shape[0]
    Input_u = []
    
    # Create discretized AIS based on bounds and resolution information.
    for i in range(nInput):
        Input_u.append(list(np.linspace(domain_bound[i,0],
                                        domain_bound[i,1],
                                        domain_resolution[i])))
   
    domain_set = np.zeros(domain_resolution + [nInput])
    image_set = np.zeros(domain_resolution + [nInput])*np.nan
    image_set[0,0] = sol.x
    
    for i in range(numInput):
        inputID = [0]*nInput
        inputID[0] = int(np.mod(i, domain_resolution[0]))
        domain_val = [Input_u[0][inputID[0]]]
        
        for j in range(1,nInput):
            inputID[j] = int(np.mod( np.floor(i/np.prod(domain_resolution[0:j])),
                                    domain_resolution[j]))
            domain_val.append(Input_u[j][inputID[j]])
        
        domain_set[tuple(inputID)] = domain_val
         
    
    cube_vertices = list()
    for n in range(2**(nInput)):
        #print(n)
        cube_vertices.append( [int(x) for x in 
                               np.binary_repr(n, width=nInput)])
    
    domain_polyhedra = list()
    for i in range(numInput):
        inputID[0] = int(np.mod(i, domain_resolution[0]))
        
        
        for j in range(1,nInput):
            inputID[j] = int(np.mod( np.floor(i/np.prod(domain_resolution[0:j])),
                                    domain_resolution[j]))
        
        
        if np.prod(inputID) != 0:
            inputID = [x-1 for x in inputID]
            ID = np.array([inputID]*(2**(nInput)))+ np.array(cube_vertices)
            
            V_domain_id = np.zeros((nInput,2**(nInput)))
            V_image_id = np.zeros((nOutput,2**(nInput)))
            for k in range(2**(nInput)):
                ID_cell = tuple([int(x) for x in ID[k]])
                
                if k == 0:
                    domain_0 = domain_set[ID_cell]
                    image_0 = image_set[ID_cell]
                    V_domain_id[:,k] = domain_0
                    V_image_id[:,k] = image_0
                    # print('Domain 0')
                    # print(domain_0)
                    
                    # print('image 0')
                    # print(image_0)
                    # print('dFdi')
                    # print(dFdi(domain_0,image_0))
                    # print('dFdo')
                    # print(dFdo(domain_0,image_0))
                    # print('dodi0')
                    # print(dodi(domain_0,image_0))
                    
                else:
                    domain_k = domain_set[ID_cell]
                    V_domain_id[:,k] = domain_k
                    
                    #sol = root(F_io, image_0,args=domain_k)
                    sol = root(F_io, image_0, args=domain_k)

                    image_k = predict_eEuler(dodi,domain_0,domain_k,image_0)

                    image_set[ID_cell] = sol.x
                    V_image_id[:,k] = sol.x
                    
                    print('Explicit solution')
                    print(shower(domain_k))
                    
                    print('Implicit solution')
                    print(sol.x)
                    
                    print('Estimated Euler implicit solution')
                    print(image_k)
                    
                    print('Estimated RK4 implicit solution')
                    print(predict_RK4(dodi,domain_0,domain_k,image_0))
                    
                    print()
            domain_polyhedra.append(V_domain_id)
    return image_set

# %% Continuation methods
def predict_odeint(dodi, i0, iplus ,o0):
    k = np.sqrt((i0 - iplus)**2 )
    output_plus = 0
    return output_plus

def predict_RK4(dodi,i0, iplus ,o0):
    h = iplus -i0

    k1 = h@dodi( i0          , o0           )
    k2 = h@dodi( i0 + (1/2)*h, o0 + (1/2)*k1)
    k3 = h@dodi( i0 + (1/2)*h, o0 + (1/2)*k1)
    k4 = h@dodi( i0 +       h, o0 +       k3)
    return o0 + (1/6)*(k1 + 2*k2 + 2*k3 + k4)

def predict_eEuler(dodi,i0, iplus ,o0):
    return o0 + dodi(i0,o0)@(iplus -i0)

# %% Test area! REMOVE BEFORE RELEASE!!!!
def shower_implicit(u,y):
    d = jnp.zeros(2)
    LHS1 = y[0] - (u[0]+u[1])
    # LHS2 = y[1] - (u[0]*(60+d[0])+u[1]*(120+d[1]))/(u[0]+u[1])
    if y[0]!=0:
        LHS2 = y[1] - (u[0]*(60+d[0])+u[1]*(120+d[1]))/(u[0]+u[1])
    else:
        LHS2 = y[1] - (60+120)/2
    
    return jnp.array([LHS1, LHS2])
def shower(u):
    y = np.zeros(2)
    d = jnp.zeros(2)
    y[0] = (u[0]+u[1])
    # LHS2 = y[1] - (u[0]*(60+d[0])+u[1]*(120+d[1]))/(u[0]+u[1])
    if y[0]!=0:
        y[1] = (u[0]*(60+d[0])+u[1]*(120+d[1]))/(u[0]+u[1])
    else:
        y[1] = (60+120)/2
    
    return jnp.array(y)

def FF1(u):
    y = np.zeros(2)
    # y[0] = u[1]**2*u[0]
    y[0] = u[0] - 2*u[1]
    y[1] = 3*u[0] + 4*u[1]
    return jnp.array(y)

def FF1_implicit(u,y):
    # LHS0 = y[0] - u[1]**2*u[0]
    LHS0 = y[0] - (u[0] - 2*u[1])
    LHS1 = y[1] - (3*u[0] + 4*u[1])
    return jnp.array([LHS0, LHS1])
#%% Test run
AIS_bound = np.array([[1.0, 10],
                    [1.0, 10]])

# AIS_bound = np.array([[10.0, 100.0],
#                     [0.5, 2.0]])

AISresolution = [5, 5]

output_init = np.array([0.0, 10.0])
slack = implicit_map(shower_implicit, AIS_bound, AISresolution, output_init)

print(slack)