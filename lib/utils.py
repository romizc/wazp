import matplotlib
import numpy as np
import matplotlib.pyplot as plt
import astropy.io.fits as fits
import os, sys
from astropy.cosmology.core import FlatLambdaCDM as flat
from astropy import units as u
from astropy.convolution import convolve,Gaussian1DKernel
import healpy as hp
from math import log, exp, atan, atanh
from astropy.table import Table
from scipy.optimize import least_squares
from scipy import interpolate



def create_directory(dir):
    """_summary_

    Args:
        dir (_type_): _description_
    """
    if not os.path.exists(dir):
        os.mkdir(dir)
    return


def read_FitsCat(cat):
    """_summary_

    Args:
        cat (_type_): _description_

    Returns:
        _type_: _description_
    """
    hdulist=fits.open(cat)
    dat=hdulist[1].data
    hdulist.close()
    return dat


def read_FitsFootprint(hpx_footprint, hpx_meta):
    """_summary_

    Args:
        hpx_footprint (_type_): _description_
        hpx_meta (_type_): _description_

    Returns:
        _type_: _description_
    """

    hdulist=fits.open(hpx_footprint)
    dat = hdulist[1].data
    hdulist.close()
    hpix_map = dat[hpx_meta['key_pixel']].astype(int)
    if hpx_meta['key_frac'] == 'none':
        frac_map = np.ones(len(hpix_map0)).astype(float)
    else:
        frac_map = dat[hpx_meta['key_frac']]
    return  hpix_map, frac_map


def read_mosaicFitsCat_in_disc (galcat, tile, radius_deg):
    """From a list of galcat files, selects objects in a cone centered 
    on racen, deccen Output is a structured array

    Args:
        galcat (_type_): _description_
        tile (_type_): _description_
        radius_deg (_type_): _description_

    Returns:
        _type_: _description_
    """

    # tile 
    racen, deccen = tile['ra'], tile['dec']
    # list of available galcats => healpix pixels 
    gdir = galcat['mosaic']['dir']
    raw_list = np.array(os.listdir(gdir))
    hpix_fits = np.array(
        [os.path.splitext(x)[0] for x in raw_list]
    ).astype(int)
    extension = os.path.splitext(raw_list[0])[1]

    # find list of fits intersection cluster field
    Nside_fits, nest_fits = galcat['mosaic']['Nside'],\
                            galcat['mosaic']['nest']
    fits_pixels_in_disc = hp.query_disc(
        nside=Nside_fits, nest=nest_fits, 
        vec=hp.ang2vec(racen, deccen, lonlat=True),
        radius = np.radians(radius_deg), inclusive=True
    )
    relevant_fits_pixels = fits_pixels_in_disc\
                           [np.isin(
                               fits_pixels_in_disc, 
                               hpix_fits, 
                               assume_unique=True
                           )]

    if len(relevant_fits_pixels) > 0:
        # merge intersecting fits 
        for i in range (0, len(relevant_fits_pixels)):
            dat_disc = read_FitsCat(
                os.path.join(gdir, str(relevant_fits_pixels[i])+extension)
            )
            dcen = np.degrees( 
                dist_ang(
                    dat_disc[galcat['keys']['key_ra']], 
                    dat_disc[galcat['keys']['key_dec']],
                    racen, deccen
                )
            )
            if i == 0:
                data_gal_disc = np.copy(dat_disc[dcen<radius_deg])
            else:
                data_gal_disc = np.append(
                    data_gal_disc, 
                    dat_disc[dcen<radius_deg]
                )
    else:
        data_gal_disc = None
    return data_gal_disc


def read_mosaicFootprint_in_disc (footprint, tile, radius_deg):
    """From a list of galcat files, selects objects in a cone 
    centered on racen, deccen
    Output is a structured array

    Args:
        footprint (_type_): _description_
        tile (_type_): _description_
        radius_deg (_type_): _description_

    Returns:
        _type_: _description_
    """

    # tile 
    racen, deccen = tile['ra'], tile['dec']
    # list of available galcats => healpix pixels 
    gdir = footprint['mosaic']['dir']
    raw_list = np.array(os.listdir(gdir))
    hpix_fits = np.array(
        [os.path.splitext(x)[0].replace('_footprint','') for x in raw_list]
    ).astype(int)
    extension = os.path.splitext(raw_list[0])[1]
    # find list of fits intersection cluster field
    Nside_fits, nest_fits = footprint['mosaic']['Nside'],\
                            footprint['mosaic']['nest']
    fits_pixels_in_disc = hp.query_disc(
        nside=Nside_fits, nest=nest_fits, 
        vec=hp.ang2vec(racen, deccen, lonlat=True),
        radius = np.radians(radius_deg), 
        inclusive=True
    )
    relevant_fits_pixels = fits_pixels_in_disc\
                           [np.isin(
                               fits_pixels_in_disc, 
                               hpix_fits, 
                               assume_unique=True
                           )]
    if len(relevant_fits_pixels) > 0:
        # merge intersecting fits 
        for i in range (0, len(relevant_fits_pixels)):
            dat_disc = read_FitsCat(
                os.path.join(
                    gdir, 
                    str(relevant_fits_pixels[i])+'_footprint'+extension
                )
            )
            ra, dec = hp.pix2ang(
                footprint['Nside'],
                dat_disc[footprint['key_pixel']],
                footprint['nest'], 
                lonlat=True
            )
            dcen = np.degrees(dist_ang(ra, dec, racen, deccen))
            if i == 0:
                data_fp_disc = np.copy(dat_disc[dcen<radius_deg])
            else:
                data_fp_disc = np.append(
                    data_fp_disc, 
                    dat_disc[dcen<radius_deg]
                )
    else:
        data_fp_disc = None

    return data_fp_disc


def read_mosaicFitsCat_in_hpix (galcat, hpix_tile, Nside_tile, nest_tile):
    """_summary_

    Args:
        footprint (_type_): _description_
        hpix_tile (_type_): _description_
        Nside_tile (_type_): _description_
        nest_tile (_type_): _description_

    Returns:
        _type_: _description_
    """
    """
    From a list of galcat files, selects objects in a cone 
    centered on racen, deccen
    Output is a structured array
    """
    # list of available galcats => healpix pixels 
    gdir = galcat['mosaic']['dir']
    raw_list = np.array(os.listdir(gdir))
    hpix_fits = np.array(
        [os.path.splitext(x)[0] for x in raw_list]
    ).astype(int)
    extension = os.path.splitext(raw_list[0])[1]
    Nside_fits, nest_fits = galcat['mosaic']['Nside'], galcat['mosaic']['nest']

    # warning we assume Nside_tile > Nside_fits !!
    ra_fits, dec_fits = hp.pix2ang(
        Nside_fits, hpix_fits, nest_fits, lonlat=True 
    )
    hpix_fits_tile = hp.ang2pix(
        Nside_tile, ra_fits, dec_fits, nest_tile, lonlat=True
    )
    relevant_fits_pixels = np.unique(
        hpix_fits[np.isin(hpix_fits_tile, hpix_tile)]
    )
    if len(relevant_fits_pixels) > 0:
        # merge intersecting fits 
        for i in range (0, len(relevant_fits_pixels)):
            dat = read_FitsCat(
                os.path.join(gdir, str(relevant_fits_pixels[i])+extension)
            )
            if i == 0:
                data_gal_hpix = np.copy(dat)
            else:
                data_gal_hpix = np.append(data_gal_hpix, dat)
    else:
        data_gal_hpix = None
    return data_gal_hpix


def read_mosaicFootprint_in_hpix (footprint, hpix_tile, Nside_tile, nest_tile):
    """_summary_

    Args:
        footprint (_type_): _description_
        hpix_tile (_type_): _description_
        Nside_tile (_type_): _description_
        nest_tile (_type_): _description_

    Returns:
        _type_: _description_
    """

    # list of available footprints => healpix pixels 
    gdir = footprint['mosaic']['dir']
    raw_list = np.array(os.listdir(gdir))
    hpix_fits = np.array(
        [os.path.splitext(x)[0].replace('_footprint','') for x in raw_list]
    ).astype(int)
    extension = os.path.splitext(raw_list[0])[1]
    Nside_fits, nest_fits = footprint['mosaic']['Nside'],\
                            footprint['mosaic']['nest']

    # warning we assume Nside_tile > Nside_fits !!
    ra_fits, dec_fits = hp.pix2ang(
        Nside_fits, hpix_fits, nest_fits, lonlat=True 
    )
    hpix_fits_tile = hp.ang2pix(
        Nside_tile, ra_fits, dec_fits, nest_tile, lonlat=True
    )

    relevant_fits_pixels = np.unique(
        hpix_fits[np.isin(hpix_fits_tile, hpix_tile)]
    )

    if len(relevant_fits_pixels) > 0:
        # merge intersecting fits 
        for i in range (0, len(relevant_fits_pixels)):
            dat = read_FitsCat(
                os.path.join(
                    gdir, 
                    str(relevant_fits_pixels[i])+'_footprint'+extension
                )
            )
            if i == 0:
                data_fp_hpix = np.copy(dat)
            else:
                data_fp_hpix = np.append(data_fp_hpix, dat)
    else:
        data_fp_hpix = None
    return data_fp_hpix


def create_survey_footprint_from_mosaic(footprint, survey_footprint):
    """_summary_

    Args:
        footprint (_type_): _description_
        fpath (_type_): _description_
    """
    all_files = np.array(os.listdir(footprint['mosaic']['dir']))
    flist = [os.path.join(footprint['mosaic']['dir'], f) for f in all_files]
    concatenate_fits(flist, survey_footprint)
    return


def create_mosaic_footprint(footprint, fpath):
    """_summary_

    Args:
        footprint (_type_): _description_
        fpath (_type_): _description_
    """
    # from a survey footprint create a mosaic of footprints at lower resol.
    if not os.path.exists(fpath):
        os.mkdir(fpath)
    hpix0, frac0 = read_FitsFootprint(
        footprint['survey_footprint'], footprint
    )
    ra0, dec0 = hp.pix2ang(
        footprint['Nside'], hpix0, footprint['nest'], lonlat=True 
    )
    hpix = hp.ang2pix(
        footprint['mosaic']['Nside'], ra0, dec0, footprint['mosaic']['nest'], 
        lonlat=True
    )
    for hpu in np.unique(hpix):
        all_cols = fits.ColDefs([
            fits.Column(
                name = footprint['key_pixel'],  
                format = 'K',
                array = hpix0[np.isin(hpix, hpu)]
            ),
            fits.Column(
                name='ra',       
                format='E',
                array= ra0[np.isin(hpix, hpu)]
            ),
            fits.Column(
                name='dec',      
                format='E',
                array= dec0[np.isin(hpix, hpu)]
            ),
            fits.Column(
                name=footprint['key_frac'],   
                format='K',
                array= frac0[np.isin(hpix, hpu)]
            )
        ])
        hdu = fits.BinTableHDU.from_columns(all_cols)
        hdu.writeto(
            os.path.join(fpath, str(hpu)+'_footprint.fits'),
            overwrite=True
        )
    return


def concatenate_fits(flist, output):
    """_summary_

    Args:
        flist (_type_): _description_
        output (_type_): _description_

    Returns:
        _type_: _description_
    """

    for i in range (0, len(flist)):
        dat = read_FitsCat(flist[i])
        if i == 0:
            cdat = np.copy(dat)
        else:
            cdat = np.append(cdat, dat)
    t = Table(cdat)#, names=names)
    t.write(output, overwrite=True)
    return cdat


def concatenate_fits_with_label(flist, label_name, label, output):
    """_summary_

    Args:
        flist (_type_): _description_
        label_name (_type_): _description_
        label (_type_): _description_
        output (_type_): _description_

    Returns:
        _type_: _description_
    """
    for i in range (0, len(flist)):
        dat = read_FitsCat(flist[i])
        datL = Table(dat)
        datL[label_name] = int(label[i])*np.ones(len(dat)).astype(int)
        if i == 0:
            cdat = np.copy(datL)
        else:
            cdat = np.append(cdat, datL)
    t = Table(cdat)#, names=names)
    t.write(output, overwrite=True)
    return cdat


def add_key_to_fits(fitsfile, key_val, key_name, key_type):
    """_summary_

    Args:
        fitsfile (_type_): _description_
        key_val (_type_): _description_
        key_name (_type_): _description_
        key_type (_type_): _description_
    """
    hdulist = fits.open(fitsfile)
    dat=hdulist[1].data
    hdulist.close()

    orig_cols = dat.columns
    if key_type == 'float':
        new_col = fits.ColDefs([
            fits.Column(name=key_name, format='E',array=key_val)])
    if key_type == 'int':
        new_col = fits.ColDefs([
            fits.Column(name=key_name, format='J',array=key_val)])

    hdu = fits.BinTableHDU.from_columns(orig_cols + new_col)    
    hdu.writeto(fitsfile, overwrite = True)
    return

        
def filter_hpx_tile(data, cat, tile_specs):
    """_summary_

    Args:
        data (_type_): _description_
        cat (_type_): _description_
        tile_specs (_type_): _description_

    Returns:
        _type_: _description_
    """
    ra, dec = data[cat['keys']['key_ra']],\
              data[cat['keys']['key_dec']]
    Nside, nest = tile_specs['Nside'], tile_specs['nest']
    pixel_tile = tile_specs['hpix']
    hpx = hp.ang2pix(Nside, ra, dec, nest, lonlat=True)
    return data[np.argwhere(hpx == pixel_tile).T[0]]


def filter_disc_tile(data, cat, tile_specs):
    """_summary_

    Args:
        data (_type_): _description_
        cat (_type_): _description_
        tile_specs (_type_): _description_

    Returns:
        _type_: _description_
    """
    ra, dec = data[cat['keys']['key_ra']],\
              data[cat['keys']['key_dec']]
    ra_tile, dec_tile = tile_specs['ra'], tile_specs['ra']
    radius_tile_deg = tile_specs['radius_tile_deg']
    dcen_deg = np.degrees(dist_ang(ra, dec, ra_tile, dec_tile))
    return data[dcen_deg<=radius_tile_deg]


def add_hpx_to_cat(data_gal, ra, dec, Nside_tmp, nest_tmp, keyname):
    """_summary_

    Args:
        data_gal (_type_): _description_
        ra (_type_): _description_
        dec (_type_): _description_
        Nside_tmp (_type_): _description_
        nest_tmp (_type_): _description_
        keyname (_type_): _description_

    Returns:
        _type_: _description_
    """
    ghpx = hp.ang2pix(Nside_tmp, ra, dec, nest_tmp, lonlat=True)
    t = Table (data_gal)
    t[keyname] = ghpx
    return t


def mad(x):
    """_summary_

    Args:
        x (_type_): _description_

    Returns:
        _type_: _description_
    """
    return 1.4826*np.median(abs(x))


def gaussian(x, mu, sig):
    """_summary_

    Args:
        x (_type_): _description_
        mu (_type_): _description_
        sig (_type_): _description_

    Returns:
        _type_: _description_
    """
    return np.exp(-(x - mu)**2 / (2.*sig**2) ) / (sig * np.sqrt(2.*np.pi))


def dist_ang(ra1, dec1, ra_ref, dec_ref):
    """_summary_

    Args:
        ra1 (_type_): _description_
        dec1 (_type_): _description_
        ra_ref (_type_): _description_
        dec_ref (_type_): _description_

    Returns:
        _type_: _description_
    """
    """
    angular distance between (ra1, dec1) and (ra_ref, dec_ref)
    ra-dec in degrees
    ra1-dec1 can be arrays 
    ra_ref-dec_ref are scalars
    output is in radian
    """
    costheta = np.sin(np.radians(dec_ref)) * np.sin(np.radians(dec1)) +\
               np.cos(np.radians(dec_ref)) * np.cos(np.radians(dec1)) *\
               np.cos(np.radians(ra1-ra_ref))
    costheta[costheta>1.] = 1.
    costheta[costheta<-1.] = -1.
    dist_ang = np.arccos(costheta)
    return dist_ang 


def area_ann_deg2(theta_1, theta_2):
    """_summary_

    Args:
        theta_1 (_type_): _description_
        theta_2 (_type_): _description_

    Returns:
        _type_: _description_
    """
    area = 2. * np.pi * (np.cos(np.radians(theta_1)) -\
                         np.cos(np.radians(theta_2))) *\
        (180./np.pi)**2
    return area


def _mstar_ (mstar_filename, zin):
    """
    from a given (z, mstar) ascii file
    interpolate to provide the mstar at a given z_in
    """
    zst, mst = np.loadtxt(mstar_filename, usecols=(0, 1), unpack=True)
    return np.interp (zin,zst,mst)


def join_struct_arrays(arrays):
    """_summary_

    Args:
        arrays (_type_): _description_

    Returns:
        _type_: _description_
    """
    sizes = np.array([a.itemsize for a in arrays])
    offsets = np.r_[0, sizes.cumsum()]
    n = len(arrays[0])
    joint = np.empty((n, offsets[-1]), dtype=np.uint8)
    for a, size, offset in zip(arrays, sizes, offsets):
        joint[:,offset:offset+size] = a.view(np.uint8).reshape(n,size)
        #print ('desc ', a.dtype.descr)
    dtype = sum((a.dtype.descr for a in arrays), [])
    return joint.ravel().view(dtype)

def radec_window_area (ramin, ramax, decmin, decmax):
    """_summary_

    Args:
        ramin (_type_): _description_
        ramax (_type_): _description_
        decmin (_type_): _description_
        decmax (_type_): _description_

    Returns:
        _type_: _description_
    """
    nstep = int((decmax-decmin)/0.1)+1
    step = (decmax-decmin)/float(nstep)
    decmini = np.arange(decmin, decmax, step)
    decmaxi = decmini+step
    decceni = (decmini + decmaxi)/2.
    darea = (ramax-ramin)*np.cos(np.pi*decceni/180.)*(decmaxi-decmini)
    return np.sum(darea)


# healpix functions
def sub_hpix(hpix, Nside, nest):
    """_summary_

    Args:
        hpix (_type_): _description_
        Nside (_type_): _description_
        nest (_type_): _description_

    Returns:
        _type_: _description_
    """
    # from a list of pixels at resolution Nside 
    # get the corresponding list at resolution Nside*2
    rac, decc = np.zeros(4*len(hpix)), np.zeros(4*len(hpix))
    i=0
    for p in hpix:
        ra, dec = hp.vec2ang(hp.boundaries(Nside, p, 1, nest).T, lonlat=True)
        racen, deccen = hp.pix2ang(Nside, p, nest, lonlat=True)
        for j in range(0,4):
            rac[i], decc[i] = (ra[j]+racen)/2., (dec[j]+deccen)/2. 
            i+=1
    return hp.ang2pix(Nside*2, rac, decc, nest, lonlat=True)


def makeHealpixMap(ra, dec, weights=None, nside=1024, nest=False):
    """_summary_

    Args:
        ra (_type_): _description_
        dec (_type_): _description_
        weights (_type_, optional): _description_. Defaults to None.
        nside (int, optional): _description_. Defaults to 1024.
        nest (bool, optional): _description_. Defaults to False.

    Returns:
        _type_: _description_
    """
    # convert a ra/dec catalog into healpix map with counts pe_r cell
    ipix = hp.ang2pix(nside, (90-dec)/180*np.pi, ra/180*np.pi, nest=nest)
    return np.bincount(ipix, weights = weights, minlength=hp.nside2npix(nside))


def all_hpx_in_annulus (ra, dec, radius_in_deg, radius_out_deg, 
                        hpx_meta, inclusive):
    """
    Get the list of all healpix pixels falling in an annulus around 
    ra-dec (deg) 
    the radii that define the annulus are in degrees    
    pixels are inclusive on radius_out but not radius_in
    """
    Nside, nest = hpx_meta['Nside'], hpx_meta['nest']
    pixels_in_disc = hp.query_disc(
        nside=Nside, nest=nest, 
        vec=hp.ang2vec(ra, dec, lonlat=True),
        radius = np.radians(radius_out_deg), 
        inclusive=inclusive
    )
    if radius_in_deg>0.:
        pixels_in_disc_in = hp.query_disc(
            nside=Nside, nest=nest, 
            vec=hp.ang2vec(ra, dec, lonlat=True),
            radius = np.radians(radius_in_deg), 
            inclusive=inclusive
        )
        id_annulus = np.isin(
            pixels_in_disc, 
            pixels_in_disc_in, 
            assume_unique=True, 
            invert=True
        )
        pixels_in_ann = pixels_in_disc[id_annulus]
    else:
        pixels_in_ann = np.copy(pixels_in_disc)

    return pixels_in_ann

def hpx_in_annulus (ra, dec, radius_in_deg, radius_out_deg, 
                    data_fp, hpx_meta, inclusive):
    """
    Given an array of healpix pixels (hpix, frac) where frac is the 
    covered fraction of each hpix pixel,
    computes the sub list of these pixels falling in an annulus around position 
    ra-dec (deg)
    the radii that define the annulus are in degrees
    hpx pixels are inclusive on radius_out but not radius_in
    """
    Nside, nest = hpx_meta['Nside'], hpx_meta['nest']
    hpix, frac = data_fp[hpx_meta['key_pixel']], data_fp[hpx_meta['key_frac']]

    area_pix = hp.nside2pixarea(Nside, degrees=True)
    pixels_in_ann = all_hpx_in_annulus (
        ra, dec, radius_in_deg, radius_out_deg, hpx_meta, inclusive
    )
    npix_all = len(pixels_in_ann)
    area_deg2 = 0.
    coverfrac = 0.
    hpx_in_ann, frac_in_ann = [], []

    if npix_all > 0:
        idx = np.isin(hpix, pixels_in_ann)
        hpx_in_ann = hpix[idx]  # visible pixels
        frac_in_ann = frac[idx] 
        npix = len(hpx_in_ann)
        if npix > 0:
            area_deg2 = np.sum(frac_in_ann) * area_pix
            coverfrac = np.sum(frac_in_ann)/float(npix_all)
    return hpx_in_ann, frac_in_ann, area_deg2, coverfrac


# FCT to split surveys 
def survey_ra_minmax(ra):
    """_summary_

    Args:
        ra (_type_): _description_

    Returns:
        _type_: _description_
    """
    ramin, ramax = np.amin(ra), np.amax(ra)
    if ramin<0.5 and ramax>359.5:
        nbins = 360
        hist, bin_edges = np.histogram(ra, bins=nbins, range=(0., 360))
        ramin_empty = bin_edges[np.amin ( np.argwhere(hist==0 ))]
        ramax_empty = bin_edges[np.amax ( np.argwhere(hist==0 ))]
        
        ra1 = ra[(ra<ramin_empty+1.)]
        ra2 = ra[(ra>ramax_empty-1.)]-360.
        ra_new = np.hstack((ra1, ra2))
        ramin, ramax = np.amin(ra_new), np.amax(ra_new)
    return ramin, ramax


def hpx_degrade(pix_in, nside_in, nest_in, nside_out, nest_out):
    """_summary_

    Args:
        pix_in (_type_): _description_
        nside_in (_type_): _description_
        nest_in (_type_): _description_
        nside_out (_type_): _description_
        nest_out (_type_): _description_

    Returns:
        _type_: _description_
    """
    ra, dec = hp.pix2ang(nside_in, pix_in, nest_in, lonlat=True)
    pix_out0 = hp.ang2pix(nside_out, ra, dec, nest_out, lonlat=True)
    pix_out, counts = np.unique(pix_out0, return_counts=True)
    nsamp = (float(nside_in)/float(nside_out))**2
    return pix_out, counts.astype(float)/nsamp

def hpx_split_survey (footprint_file, footprint, admin, output):
    """_summary_

    Args:
        footprint_file (_type_): _description_
        footprint (_type_): _description_
        admin (_type_): _description_
        output (_type_): _description_

    Returns:
        _type_: _description_
    """
    Nside_fp  , nest_fp   = footprint['Nside'], footprint['nest']
    Nside_tile, nest_tile = admin['Nside'], admin['nest']

    dat = read_FitsCat(footprint_file)
    hpix_map, frac_map = dat[footprint['key_pixel']], \
                         dat[footprint['key_frac']]

    hpix_tile, frac_tile = hpx_degrade(
        hpix_map, Nside_fp, nest_fp, Nside_tile, nest_tile
    )
    racen, deccen = hp.pix2ang(Nside_tile, hpix_tile, nest_tile, lonlat=True)
    area_tile = hp.nside2pixarea(Nside_tile, degrees=True)

    # tiles 
    data_tiles = np.zeros( (len(hpix_tile)), 
                           dtype={
                               'names':(
                                   'id', 'hpix', 
                                   'ra', 'dec', 
                                   'area_deg2', 'eff_area_deg2',
                                   'Nside', 'nest'
                               ), 
                                  'formats':(
                                      'i8', 'i8', 
                                      'f8', 'f8', 
                                      'f8', 'f8', 
                                      'i8', 'b'
                                  ) 
                           }
    )
    data_tiles['id'] = np.arange(len(hpix_tile))
    data_tiles['hpix'] = hpix_tile
    data_tiles['ra'], data_tiles['dec'] = np.around(racen,4),\
                                          np.around(deccen,4)
    data_tiles['area_deg2'] = np.around(area_tile,4)
    data_tiles['eff_area_deg2'] = np.around(frac_tile*area_tile,4)
    data_tiles['Nside'] = Nside_tile *np.ones(len(hpix_tile)).astype(int)
    data_tiles['nest'] = len(hpix_tile)*[nest_tile]

    t = Table (data_tiles)
    t.write(output, overwrite=True)
    print ('.....tile area (deg2) = ', 
           np.round(hp.nside2pixarea(Nside_tile, degrees=True), 2)
    )
    print ('.....effective survey area (deg2) = ', 
           np.around(np.sum(frac_tile)*area_tile,4)
    )
    return len(data_tiles)


def tile_radius(tiling):
    """_summary_

    Args:
        tiling (_type_): _description_

    Returns:
        _type_: _description_
    """

    Nside_tile = tiling['Nside']
    frame_deg = tiling['overlap_deg']
    tile_radius = (2.*\
                   hp.nside2pixarea(Nside_tile, degrees=True))**0.5 / 2.
    return tile_radius + frame_deg


def disc_coverfrac(ra, dec, radius_deg, dat_footprint, footprint):
    pixels_in_disc = hp.query_disc(
        nside = footprint['Nside'], 
        nest = footprint['nest'],  
        vec = hp.ang2vec(ra, dec, lonlat=True),
        radius = np.radians(radius_deg), 
        inclusive=True
    )
    fhpx = dat_footprint[footprint['key_pixel']]
    ind_in = np.isin (pixels_in_disc, fhpx)
    return float(len(pixels_in_disc[ind_in])) / float(len(pixels_in_disc))


def create_tile_specs(tile, tile_radius_deg, admin, 
                      search_radius, radius_unit, 
                      dat_footprint, footprint):
    """_summary_

    Args:
        tile (_type_): _description_
        tile_radius_deg (_type_): _description_
        admin (_type_): _description_

    Returns:
        _type_: _description_
    """
    frac_map = dat_footprint[footprint['key_frac']]
    disc_eff_area_deg2 = np.sum(frac_map) * \
                         hp.nside2pixarea(footprint['Nside'], degrees=True)


    if admin['target_mode']:
        # coverfrac in  30 and 5 arcmin
        coverfrac_30 = disc_coverfrac(
            tile['ra'], tile['dec'], 0.5, dat_footprint, footprint
        )
        coverfrac_5 = disc_coverfrac(
            tile['ra'], tile['dec'], 1./12., dat_footprint, footprint
        )
        hpix = -1
        Nside, nest = -1, None
        area_deg2 = np.round(area_ann_deg2(0., tile_radius_deg), 3)
        eff_area_deg2 = disc_eff_area_deg2
        if radius_unit == 'arcmin':
            radius_filter_deg = search_radius/60.
        if radius_unit == 'mpc':
            radius_filter_deg = np.degrees(
                (search_radius/60.) / target['conv_factor']
            )
    else:
        coverfrac_30 = -1.
        coverfrac_5 = -1. 
        hpix = tile['hpix']
        Nside, nest = admin['tiling']['Nside'], admin['tiling']['nest']
        area_deg2 = tile['area_deg2']
        eff_area_deg2 = tile['eff_area_deg2']
        radius_filter_deg = -1.

    tile_specs = {'id':tile['id'],
                  'ra': tile['ra'], 'dec': tile['dec'],
                  'hpix': hpix,
                  'Nside': Nside,
                  'nest': nest,
                  'area_deg2': area_deg2,
                  'eff_area_deg2': eff_area_deg2,
                  'disc_eff_area_deg2': disc_eff_area_deg2,
                  'radius_tile_deg': np.round(tile_radius_deg, 3), 
                  'radius_filter_deg': np.round(radius_filter_deg, 3), 
                  'coverfrac_30arcmin': np.round(coverfrac_30, 2),
                  'coverfrac_5arcmin': np.round(coverfrac_5, 2),
                  'target_mode': admin['target_mode'] }

    return tile_specs 


def cond_in_disc(rag, decg, hpxg, Nside, nest, racen, deccen, rad_deg):
    """_summary_

    Args:
        rag (_type_): _description_
        decg (_type_): _description_
        hpxg (_type_): _description_
        Nside (_type_): _description_
        nest (_type_): _description_
        racen (_type_): _description_
        deccen (_type_): _description_
        rad_deg (_type_): _description_

    Returns:
        _type_: _description_
    """

    pix_size = (hp.nside2pixarea(Nside, degrees=True))**0.5
    dist2cl = np.ones(len(rag))*2.*rad_deg

    pixels_in_disc = hp.query_disc(
        nside = Nside, nest=nest, 
        vec = hp.ang2vec(racen, deccen, lonlat=True),
        radius = np.radians(rad_deg), 
        inclusive=True
    )
    if pix_size > 0.1*rad_deg:
        cond = np.isin(hpxg, pixels_in_disc)
        dist2cl[cond] = np.degrees(
            dist_ang(
                rag[cond], decg[cond], racen, deccen
            )
        )
    else: 
        pixels_in_disc_strict = hp.query_disc(
            nside = Nside, nest=nest, 
            vec = hp.ang2vec(racen, deccen, lonlat=True),
            radius = np.radians(0.8*rad_deg), 
            inclusive = False
        )
        pixels_edge = pixels_in_disc[np.isin(
            pixels_in_disc, pixels_in_disc_strict, 
            invert=True, assume_unique=True
        )]
        cond_strict = np.isin(hpxg, pixels_in_disc_strict)
        cond_edge  =  np.isin(hpxg, pixels_edge)

        dist2cl[cond_strict] = 0.
        dist2cl[cond_edge] = np.degrees(
            dist_ang(
                rag[cond_edge], decg[cond_edge], racen, deccen
            )
        )
    return (dist2cl<rad_deg)


def cond_in_hpx_disc(hpxg, Nside, nest, racen, deccen, rad_deg):
    """_summary_

    Args:
        hpxg (_type_): _description_
        Nside (_type_): _description_
        nest (_type_): _description_
        racen (_type_): _description_
        deccen (_type_): _description_
        rad_deg (_type_): _description_

    Returns:
        _type_: _description_
    """

    pixels_in_disc_strict = hp.query_disc(
        nside=Nside, nest=nest, 
        vec=hp.ang2vec(racen, deccen, lonlat=True),
        radius = np.radians(rad_deg), 
        inclusive=False
    )
    cond_strict = np.isin(hpxg, pixels_in_disc_strict)
    return cond_strict


def normal_distribution_function(x):
    value = scipy.stats.norm.pdf(x,mean,std)
    return value

def compute_gaussian_kernel_1d(kernel):
# kernel is an integer >0
    mean = 0.0 
    kk = []
    for n in range (0,3*kernel+1):
        x1 = mean - 1./2. + float(n)
        x2 = mean + 1./2. + float(n)
        res, err = quad(normal_distribution_function, x1, x2)
        kk = np.append(kk, 100.*res)
    return np.array(np.concatenate((np.sort(kk)[0:len(kk)-1], kk)))


def get_gaussian_kernel_1d(kernel):

    if kernel == 1:
        gkernel = 0.01*np.array([0.60, 6.06, 24.17, 38.29, 24.17, 6.06, 0.60])
    if kernel == 2:
        gkernel = 0.01*np.array([ 0.24, 0.924, 2.783, 6.559, 12.098, \
                                  17.467, 19.741, 17.467, 12.098, 6.559, \
                                  2.783, 0.924, 0.24])
    if kernel == 3:
        gkernel = 0.01*np.array([ 0.153, 0.391, 0.892, 1.825, 3.343, 5.487, \
                                  8.066, 10.621, 12.528, 13.237, 12.528, \
                                  10.621, 8.066, 5.487, 3.343, 1.825, 0.892,\
                                  0.391, 0.153])
    if kernel > 3:
        gkernel = compute_gaussian_kernel_1d(kernel)
    return gkernel


def concatenate_clusters(tiles_dir, infilename, clusters_outfile): 
    """_summary_

    Args:
        tiles_dir (_type_): _description_
        clusters_outfile (_type_): _description_
    """
    # assumes that clusters are called 'clusters.fits'
    # and the existence of 'tile_info.fits'
    clist = []
    for tile_dir in tiles_dir: 
        clist.append(os.path.join(tile_dir, infilename))
    clcat = concatenate_fits(clist, clusters_outfile)
    return clcat


def concatenate_members(all_tiles, list_path_members, 
                        infilename, data_clusters, members_outfile):
    # data_clusters = clusters over the whole survey
    for it in range(0, len(all_tiles)):
        tile_id = int(all_tiles['id'][it])
        clusters_tile = data_clusters[data_clusters['tile'] == tile_id]
        clusters_id_in_tile = clusters_tile['index_cl_tile']
        members = read_FitsCat(
            os.path.join(list_path_members[it], infilename)
        )
        members_kept = members[np.isin(
            members['index_cl_tile'], clusters_id_in_tile
        )]
        # sort clusters by id_in_tile 
        ids = clusters_tile[np.argsort(clusters_id_in_tile)]['id']
        nmems = clusters_tile[np.argsort(clusters_id_in_tile)]['nmem']
        idd = clusters_tile[np.argsort(clusters_id_in_tile)]['index_cl_tile']
        # sort members by id_in_tile 
        members_kept_sorted = members_kept[np.argsort(
            members_kept['index_cl_tile']
        )]
        if it == 0:
            final_members = np.copy(members_kept_sorted)
        else:
            final_members = np.hstack((final_members, members_kept_sorted))
        for i in range(0, len(clusters_id_in_tile)):
            if it == 0 and i == 0:
                ids_for_members = ids[i]*np.ones(nmems[i]).astype(int)
                tile_for_members = tile_id*np.ones(nmems[i]).astype(int)
            else:
                ids_for_members = np.hstack(
                    (ids_for_members, ids[i]*np.ones(nmems[i]).astype(int))
                )
                tile_for_members = np.hstack(
                    (tile_for_members, tile_id*np.ones(nmems[i]).astype(int))
                )
    t = Table (final_members)
    t['id_cl'] = ids_for_members
    t['tile'] = tile_for_members
    t.write(members_outfile, overwrite=True)
    return


def add_clusters_unique_id(data_clusters, clkeys):
    """_summary_

    Args:
        data_clusters (_type_): _description_
        clkeys (_type_): _description_

    Returns:
        _type_: _description_
    """
    # create a unique id 
    id_in_survey = np.arange(len(data_clusters))
    snr = data_clusters[clkeys['key_snr']]
    t = Table(data_clusters[np.argsort(-snr)])
    t['id'] = id_in_survey.astype('str')
    return t


def get_footprint(input_data_structure, footprint, workdir):

    if input_data_structure['footprint_hpx_mosaic']: 
        survey_footprint = os.path.join(
            workdir, 'footprint', 'survey_footprint.fits'
        )
        if not os.path.isfile(survey_footprint):
            create_survey_footprint_from_mosaic(
                footprint, survey_footprint
            )
    else:
        survey_footprint = footprint['survey_footprint']
    return survey_footprint


def update_data_structure(param_cfg, param_data):

    workdir = param_cfg['out_paths']['workdir']
    footprint = param_data['footprint']
    survey = param_cfg['survey']
    input_data_structure = param_data['input_data_structure']

    # create required data structure if not exist and update config 
    if not input_data_structure[survey]['footprint_hpx_mosaic']:
        create_mosaic_footprint(
            footprint[survey], os.path.join(workdir, 'footprint_mosaic')
        )
        param_data['footprint'][survey]['mosaic']['dir'] = os.path.join(
            workdir, 'footprint_mosaic'
        )

    return param_data

