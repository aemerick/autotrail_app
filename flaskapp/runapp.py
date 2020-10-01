from flaskapp import app
from flask import request, redirect, url_for, jsonify, render_template, session, send_file
from flask import Flask, Markup, Response
from flask_session import Session

import json
import ast
import uuid
import os
import numpy as np


SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
Session(app)

_m_in_mi = 1609.34
_m_in_ft = 0.3048

#from autotrail_app.run import GLOBAL_gpx_tracks

@app.route('/dev')
def dev():
    """
    Hard-code user-input to make for a faster test run of the output.
    """

    string_args = ['units']

    float_args = ['mindistance',
                      'maxdistance',
                      'minelevation',
                      'maxelevation',
                      'maxgrade',
                      'backtrack',
                      'numroutes','startlat','startlng','endlat','endlng']

    results = {'units' : 'english',
               'mindistance' : 5.0 * _m_in_mi,
               'maxdistance' : 8.0 * _m_in_mi,
               'minelevation' : 1000.0 * _m_in_ft,
               'maxelevation' : 3000.0 * _m_in_ft,
               'maxgrade' : 100.0,
               'mingrade' : 0.0,
               'backtrack' : 3,
               'numroutes' : 2,
               'startlng' :-105.27818,
               'startlat' :  39.99855,
               'endlng'   : -105.27818,
               'endlat'   :  39.99855}

    output, gpx_tracks = run_from_input(results,units =results['units'])
    du = 'mi'
    eu = 'ft'

    return redirect( url_for('model_output',
                 trailroutes=json.dumps(output),
                 #gpx_tracks=json.dumps(gpx_tracks),
                 du = du, eu = eu))


@app.route('/button/display_route', methods=["POST"])
def button_display_route(val=0):

    if request.method == 'POST':
        val = json.loads(request.data)['val']

        print('BUTTON DISPLAY:',val-1)
        array = session['gpx_tracks'][val-1]

        print(json.dumps(array))

        return json.dumps(array)


@app.route('/button/dowload_gpx', methods=['GET'])
def button_download_gpx():

    if request.method == 'GET':

        val = int(request.args.get('val','')) - 1

        print("Downloading : ",val)

        if not ('possible_routes' in session.keys()):
            raise RuntimeError


        outname = os.getcwd() + "/outputs/route_" + str(uuid.uuid4()) + ".xml"
        session['tmap'].write_gpx_file(outname, nodes = session['possible_routes'][val])

        filename = "PlanIt_route_" + str(val) + ".xml"

        return send_file(outname,
                         mimetype='text/xml',
                         attachment_filename = filename)


@app.route('/',  methods=["GET","POST"])
def homepage():

#    if request.method == "POST":
#        longitude = request.form["startng"]
#        latitude = request.form["startlat"]
#
#        print("working in homepage")
#
#
#        return render_template("index.html", error='testing')

    error    = request.args.get('error',None)
    startlat = request.args.get('startlat', '', type=float)
    startlng = request.args.get('startlng', '', type=float)
    endlat   = request.args.get('endlat', '', type=float)
    endlng   = request.args.get('endlng', '', type=float)

    return render_template("index.html", error=error,startlat=startlat,
                                         startlng=startlng,
                                         endlat=endlat, endlng=endlng)
    #                                     hdr_txt=hdr_txt,
#                                         script_txt=script_txt,
#                                         error=error)

@app.route('/model_input', methods=['POST'])
def model_input():

    if request.method == 'POST':
        print('model_input request.form = ',request.form)

        string_args = ['units']
        float_args = ['mindistance',
                      'maxdistance',
                      'minelevation',
                      'maxelevation',
                      'maxgrade',
                      'backtrack',
                      'numroutes','startlat','startlng','endlat','endlng']

        results = {}

        for k in float_args:
            results[k] = request.form.get(k, '')
            if results[k] == '':
                results[k] = None
            else:
                results[k] = float(results[k])

        for k in string_args:
            results[k] = request.form.get(k, '')

        error = None
        if (results['mindistance'] is None) and (results['maxdistance'] is None):
            error = "Currently, both min and max distances MUST be provided. Please try again."
        elif (results['mindistance'] is None):
            results['mindistance'] = results['maxdistance']
        elif (results['maxdistance'] is None):
            results['maxdistance'] = results['mindistance']

        if not (error is None):
            return redirect(url_for('homepage', error=error)) # messages={'error':error}))

        if results['units'] == 'english':

            # need to convert to m and km
            for k in ['mindistance','maxdistance']:
                if results[k] is None:
                    continue
                results[k] *= _m_in_mi

            for k in ['minelevation','maxelevation']:
                if results[k] is None:
                    continue
                results[k] *= _m_in_ft

            du = 'mi'
            eu = 'ft'
        else:
            du = 'km'
            eu = 'm'

        output, gpx_tracks = run_from_input(results,units =results['units'])


        trailroutes = []
        dform = '{:5.1f}'
        eform = '{:6.1f}'
        for i, rp in enumerate(output):
            trailroutes.append({'route':i+1,
                           'distance':dform.format(rp['distance']),
                           'elevation_gain':eform.format(rp['elevation_gain']),
                           'elevation_loss':eform.format(rp['elevation_loss']),
                           'repeated_percent':'{:4.2f}'.format(rp['repeated_percent']),
                           'max_altitude':eform.format(rp['max_altitude']),
                           'min_altitude':eform.format(rp['min_altitude']),
                           'min_grade':'{:3.1f}'.format(rp['average_min_grade']),
                           'max_grade':'{:3.1f}'.format(rp['average_max_grade'])})

        print("output in model_input:", output)
        print("trailroutes in model_input:", trailroutes)


        session['trailroutes'] = trailroutes

        return redirect( url_for('model_output',
                         trailroutes= json.dumps(trailroutes), # json.dumps(output),
                         gpx_tracks = json.dumps(gpx_tracks),
                         #gpx_tracks=json.dumps(gpx_tracks),
                         du = du, eu = eu))



@app.route('/model_output/<trailroutes>/<du>/<eu>', methods=['GET','POST'])
def model_output(trailroutes, du, eu):
    """
    Prepare and render the results

    AJE: This is what prepares the gpx_tracks
    """
    #gpx_tracks = ''


    #all_rp = json.loads(request.args.get('trailroutes'))
    #gpx_tracks = request.args.get('gpx_tracks')
    #if not (gpx_tracks is None):
    #    try:
    #        gpx_tracks = json.loads(request.args.get('gpx_tracks'))
    #        gpx_points = []
    #
    #        for i, gp in enumerate(gpx_tracks):
    #            gpx_points.append({'route': i+1,
    #                                'gpx' : gp})
    #    except:
    #        pass


    #du = request.args.get('du')
    #eu = request.args.get('eu')

    #trailroutes = []
    #
    # for just one for now
    #

    #dform = '{:5.1f}'
    #eform = '{:6.1f}'
    #for i, rp in enumerate(all_rp):
    #    trailroutes.append({'route':i+1,
    #                   'distance':dform.format(rp['distance']),
    #                   'elevation_gain':eform.format(rp['elevation_gain']),
    #                   'elevation_loss':eform.format(rp['elevation_loss']),
    #                   'repeated_percent':'{:4.2f}'.format(rp['repeated_percent']),
    #                   'max_altitude':eform.format(rp['max_altitude']),
    #                   'min_altitude':eform.format(rp['min_altitude']),
    #                   'min_grade':'{:3.1f}'.format(rp['average_min_grade']),
    #                   'max_grade':'{:3.1f}'.format(rp['average_max_grade'])})

    if request.method == 'GET':
        return render_template("model_output.html", trailroutes=ast.literal_eval(trailroutes),
                                                #    gpx_tracks=json.dumps(ast.literal_eval(gpx_tracks)),
                                                    du=du,eu=eu)
                                                #gpx_tracks='bullshit', #json.dumps(gpx_points),
                                                #eu = 'why',
                                                #du = du,
                                                #test='test')
                                                 # I'd also tried just gpx_tracks=gpx_points without the json


#@app.route('/api/get_coords', methods=['GET'])
#def get_coords():
#    print('stupid',request.method)
#    print('help',request.args)
#    print(request.args.get('trailnum'))
#
#    track = GLOBAL_gpx_tracks[request.args.get('trailnum')]
#    print('---',track)
#    return jsonify(track)

@app.route('/mapclick')
def mapclick():
  """
  Map click action button. grab lat / long coordinates of start and end points
  """

  startlng = request.args.get('startlng', '', type=float)
  startlat = request.args.get('startlat', '', type=float)

  endlng = request.args.get('endlng','',type=float)
  endlat = request.args.get('endlat','',type=float)

  for k in ['startlng','startlat','endlng','endlat']:
      session[k] = request.args.get(k,'',type=float)

  return redirect(url_for('homepage', startlat=startlat, startlng=startlng,
                                      endlat=endlat, endlng=endlng))
  #return render_template("form.html", longitude=longitude, latitude=latitude)



def run_from_input(results, units='english'):
    """
    This needs to be moved to a compute.py (or something) file. Actually runs
    the backend from the user input.
    """
    from planit.autotrail.trailmap import TrailMap
    from planit.autotrail  import process_gpx_data as gpx_process
    from planit.osm_data import osm_process

    # outname = '/home/aemerick/code/planit/autotrail/data/boulder_area_trail_processed'
    # tmap = gpx_process.load_graph(outname)

    # hard code for now
    place_name = "Boulder, CO"

    if place_name == 'Boulder, CO':
        north = 40.100141
        west  = -105.408908
        south = 39.841447
        east  = -105.163064
    elif place_name == 'Pasadena, CA':
        north = 34.305256
        west  = -118.139268
        south = 34.166495
        east  = -117.862647
    elif place_name == 'VT':
        center = (44.524050, -72.821687)

        north = center[0] + 0.075
        south = center[0] - 0.075
        east  = center[1] + 0.075
        west  = center[1] - 0.075

    ll = (south,west)
    rr = (north,east)

    tmap = None
    if 'll' in session.keys() and 'rr' in session.keys():
        if ll == session['ll'] and rr == session['rr'] and 'tmap' in session.keys():
            tmap = session['tmap']

    if tmap is None:
        session['ll'] = ll
        session['rr'] = rr
        tmap = osm_process.osmnx_trailmap(ll=ll,rr=rr)

        session['tmap'] = tmap

    tmap.ensure_edge_attributes()

    tmap._default_weight_factors = {'distance'          : 1,
                                    'elevation_gain'    : 0,
                                    'elevation_loss'    : 0,      # off
                                    'average_grade'     : 0,
                                    'average_max_grade' : 0,
                                    'average_min_grade' : 0,
                                    'min_grade'         : 0,           # off
                                    'max_grade'         : 0,           # off
                                    'traversed_count'   : 5,    # very on
                                    'in_another_route'  : 2}

    if 'start_node' in session.keys():
        start_node = session['start_node']
    else:
        start_node = tmap.nearest_node(results['startlng'], results['startlat'])[1]
        start_node = start_node[0]
        session['start_node'] = start_node

    if 'end_node' in session.keys():
        end_node = session['end_node']
    else:
        if (results['endlat'] in [None,'']) or (not (type(results['endlat']) in [float,int])):
            end_node = start_node
        else:
            end_node = tmap.nearest_node(results['endlng'], results['endlat'])[1]
            end_node = end_node[0]

        session['end_node'] = end_node

    print("CHOSEN NODES: ", start_node, end_node)

    if (start_node == None) or (end_node == None):
        print("Cannot find a node!!")
        raise RuntimeError

    distance = 0.5*(float(results['mindistance']) + float(results['maxdistance']))

    n_routes = int(results['numroutes'])

    target_values = {'distance' : distance}

    print('---', results)
    print("---", start_node, end_node, target_values)

    _, possible_routes, scores = tmap.multi_find_route(start_node,
                                                                target_values,
                                                                n_routes=n_routes,
                                                                end_node = end_node,
                                                                reinitialize=True,
                                                                reset_used_counter=True)

    # get the dictionary of route statistics
    route_properties = [ tmap.route_properties(nodes=nodes,
                                                   verbose=True,
                                                   units=units) for nodes in possible_routes]
    for i in range(len(scores)):
        route_properties[i]['score'] = scores[i]

    gpx_tracks = [tmap.get_route_coords(nodes=nodes, coords_only=True) for nodes in possible_routes]

    session['possible_routes']  = possible_routes
    session['route_properties'] = route_properties
    session['gpx_tracks']       = gpx_tracks
    session['tmap']             = tmap


    return route_properties, gpx_tracks
