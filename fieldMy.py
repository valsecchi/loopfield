#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct  4 13:39:57 2019

@author: Valsecchi
"""

import numpy as np
from scipy import special
from mayavi import mlab

##############################################################################
# Function to caculate the Magnetic field generated by a current loop

def base_vectors(n):
    """ Returns 3 orthognal base vectors, the first one colinear to n.

        Parameters
        -----------
        n: ndarray, shape (3, )
            A vector giving direction of the basis

        Returns
        -----------
        n: ndarray, shape (3, )
            The first vector of the basis
        l: ndarray, shape (3, )
            The second vector of the basis
        m: ndarray, shape (3, )
            The first vector of the basis

    """
    # normalize n
    n = n / (n**2).sum(axis=-1)

    # choose two vectors perpendicular to n
    # choice is arbitrary since the coil is symetric about n
    if  np.abs(n[0])==1 :
        l = np.r_[n[2], 0, -n[0]]
    else:
        l = np.r_[0, n[2], -n[1]]

    l = l / (l**2).sum(axis=-1)
    m = np.cross(n, l)
    return n, l, m


def magnetic_field(r, n, r0, R):
    """
    Returns the magnetic field from an arbitrary current loop calculated from
    eqns (1) and (2) in Phys Rev A Vol. 35, N 4, pp. 1535-1546; 1987.

    Arguments
    ----------
        n: ndarray, shape (3, )
            The normal vector to the plane of the loop at the center,
            current is oriented by the right-hand-rule.
        r: ndarray, shape (m, 3)
            A position vector where the magnetic field is evaluated:
            [x1 y2 z3 ; x2 y2 z2 ; ... ]
            r is in units of d
        r0: ndarray, shape (3, )
            The location of the center of the loop in units of d: [x y z]
        R: float
            The radius of the current loop

    Returns
    --------
    B: ndarray, shape (m, 3)
        a vector for the B field at each position specified in r
        in inverse units of (mu I) / (2 pi d)
        for I in amps and d in meters and mu = 4 pi * 10^-7 we get Tesla
    """
    ### Translate the coordinates in the coil's frame
    n, l, m = base_vectors(n)

    # transformation matrix coil frame to lab frame
    trans = np.vstack((l, m, n))
    # transformation matrix to lab frame to coil frame
    inv_trans = np.linalg.inv(trans)

    # point location from center of coil
    r = r - r0
    # transform vector to coil frame
    r = np.dot(r, inv_trans)

    #### calculate field

    # express the coordinates in polar form
    x = r[:, 0]
    y = r[:, 1]
    z = r[:, 2]
    rho = np.sqrt(x**2 + y**2)
    theta = np.arctan(x/y)
    theta[y==0] = 0

    E = special.ellipe((4 * R * rho)/( (R + rho)**2 + z**2))
    K = special.ellipk((4 * R * rho)/( (R + rho)**2 + z**2))
    Bz =  1/np.sqrt((R + rho)**2 + z**2) * (
                K
              + E * (R**2 - rho**2 - z**2)/((R - rho)**2 + z**2)
              )
    Brho = z/(rho*np.sqrt((R + rho)**2 + z**2)) * (
               -K
              + E * (R**2 + rho**2 + z**2)/((R - rho)**2 + z**2)
              )
    # On the axis of the coil we get a divided by zero here. This returns a
    # NaN, where the field is actually zero :
    Brho[np.isnan(Brho)] = 0
    Brho[np.isinf(Brho)] = 0
    Bz[np.isnan(Bz)]     = 0
    Bz[np.isinf(Bz)]     = 0

    B = np.c_[np.cos(theta)*Brho, np.sin(theta)*Brho, Bz ]

    # Rotate the field back in the lab's frame
    B = np.dot(B, trans)
    return B


def display_coil(n, r0, R, half=False):
    """
    Display a coils in the 3D view.
    If half is True, display only one half of the coil.
    """
    n, l, m = base_vectors(n)
    theta = np.linspace(0, (2-half)*np.pi, 30)
    theta = theta[..., np.newaxis]
    coil = np.atleast_1d(R)*(np.sin(theta)*l + np.cos(theta)*m)
    coil += r0
    coil_x = coil[:, 0]
    coil_y = coil[:, 1]
    coil_z = coil[:, 2]
    mlab.plot3d(coil_x, coil_y, coil_z,
            tube_radius=0.01,
            name='Coil %i' % display_coil.num,
            color=(0, 0, 0))
    display_coil.num += 1
    return coil_x, coil_y, coil_z

display_coil.num = 0

##############################################################################
# The grid of points on which we want to evaluate the field
X, Y, Z = np.mgrid[-0.15:0.15:31j, -0.15:0.15:31j, -0.15:0.15:31j]
# Avoid rounding issues :
f = 1e4  # this gives the precision we are interested by :
X = np.round(X * f) / f
Y = np.round(Y * f) / f
Z = np.round(Z * f) / f

r = np.c_[X.ravel(), Y.ravel(), Z.ravel()]

##############################################################################
# The coil positions

# The center of the coil
r0 = np.r_[0, 0, 0.1]
# The normal to the coils
n  = np.r_[0, 0, 1]
# The radius
R  = 0.1

# Add the mirror image of this coils relatively to the xy plane :
r0 = np.vstack((r0, -r0 ))
R  = np.r_[R, R]
n  = np.vstack((n, n))      # Helmoltz like configuration

##############################################################################
# Calculate field
# First initialize a container matrix for the field vector :
B = np.empty_like(r)
# Then loop through the different coils and sum the fields :
for this_n, this_r0, this_R in zip(n, r0, R):
  this_n    = np.array(this_n)
  this_r0   = np.array(this_r0)
  this_R    = np.array(this_R)
  B += magnetic_field(r, this_n, this_r0, this_R)


Bx = B[:, 0]
By = B[:, 1]
Bz = B[:, 2]
Bx.shape = X.shape
By.shape = Y.shape
Bz.shape = Z.shape

Bnorm = np.sqrt(Bx**2 + By**2 + Bz**2)

##############################################################################
# Visualization

# We threshold the data ourselves, as the threshold filter produce a
# data structure inefficient with IsoSurface
Bmax = 100

Bx[Bnorm > Bmax] = 0
By[Bnorm > Bmax] = 0
Bz[Bnorm > Bmax] = 0
Bnorm[Bnorm > Bmax] = Bmax

mlab.figure(1, bgcolor=(1, 1, 1), fgcolor=(0.5, 0.5, 0.5),
               size=(480, 480))
mlab.clf()

for this_n, this_r0, this_R in zip(n, r0, R):
  display_coil(this_n, this_r0, this_R)

field = mlab.pipeline.vector_field(X, Y, Z, Bx, By, Bz,
                                  scalars=Bnorm, name='B field')
vectors = mlab.pipeline.vectors(field,
                      scale_factor=(X[1, 0, 0] - X[0, 0, 0]),
                      )
# Mask random points, to have a lighter visualization.
vectors.glyph.mask_input_points = True
vectors.glyph.mask_points.on_ratio = 6

vcp = mlab.pipeline.vector_cut_plane(field)
vcp.glyph.glyph.scale_factor=5*(X[1, 0, 0] - X[0, 0, 0])
# For prettier picture:
#vcp.implicit_plane.widget.enabled = False

iso = mlab.pipeline.iso_surface(field,
                                contours=[0.1*Bmax, 0.4*Bmax],
                                opacity=0.6,
                                colormap='YlOrRd')

# A trick to make transparency look better: cull the front face
iso.actor.property.frontface_culling = True

mlab.view(39, 74, 0.59, [.008, .0007, -.005])

mlab.show()