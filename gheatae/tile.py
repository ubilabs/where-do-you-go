import constants
from gheatae import color_scheme, provider
from pngcanvas import PNGCanvas
from random import random, Random
import logging
import gmerc
import math
from models import UserInfo

from google.appengine.api import users
log = logging.getLogger('space_level')

rdm = Random()

DOT_MULT = 3

class BasicTile(object):
  def __init__(self, user, lat_north, lng_west, range_lat, range_lng):
    userinfo = UserInfo.all().filter('user =', user).order('-created').get()
    if userinfo:
      self.level_max = userinfo.level_max
      self.color_scheme = color_scheme.color_schemes[userinfo.color_scheme]
    else:
      self.level_max = int(constants.level_const)
      self.color_scheme = color_scheme.color_schemes[constants.default_color]

    self.cache_levels = []
    for i in range(self.level_max - 1, -1, -1):
      self.cache_levels.append(int(((-(pow(float(i) - self.level_max, 2))/self.level_max) + self.level_max) / self.level_max * 255))

    if not constants.provider:
      constants.provider = provider.DBProvider()
    self.tile_img = self.plot_image(constants.provider.get_user_data(user, lat_north, lng_west, range_lat, range_lng))

  def plot_image(self, points):
    space_level = self.__create_empty_space()
    for point in points:
      self.__merge_point_in_space(space_level, point)
    return self.convert_image(space_level)

  def __merge_point_in_space(self, space_level, point):
    # By default, multiply per color point
    dot_levels, x_off, y_off = self.get_dot(point)

    for y in range(y_off, y_off + len(dot_levels)):
      if y < 0 or y >= len(space_level):
        continue
      for x in range(x_off, x_off + len(dot_levels[0])):
        if x < 0 or x >= len(space_level[0]):
          continue
        dot_level = dot_levels[y_off - y][x_off - x]
        if dot_level <= 0.:
          continue
        space_level[y][x] += dot_level

  def scale_value(self, value):
    #ret_float = math.log(max((value + 50) / 50, 1), 1.01) + 30
    #ret_float = math.log(max((value + 30) / 40, 1), 1.01) + 30
    #ret_float = math.log(max((value + 40) / 20, 1), 1.01)
    ret_float = math.log(max(value, 1), 1.1) * 4
    return int(ret_float)

  def convert_image(self, space_level):
    tile = PNGCanvas(len(space_level[0]), len(space_level), bgcolor=[0xff,0xff,0xff,0])
    temp_color_scheme = []
    for i in range(self.level_max):
      temp_color_scheme.append(self.color_scheme.canvas[self.cache_levels[i]][0])
    for y in xrange(len(space_level[0])):
      for x in xrange(len(space_level[0])):
        if len(temp_color_scheme) > 0:
          tile.canvas[y][x] = [int(e) for e in temp_color_scheme[max(0, min(len(temp_color_scheme) - 1, self.scale_value(space_level[y][x])))]]
        else:
          tile.canvas[y][x] = [0,0,0,0]
    return tile

  def calc_point(self, rad, pt_rad, weight):
    max_alpha = 100
    fraction = (rad - pt_rad) / rad
    return max_alpha * math.pow(fraction, math.pow(weight, 0.25)) * weight
    #return max_alpha * math.pow(fraction, math.pow(weight, fraction)) * weight

  def get_dot(self, point):
    #cur_dot = dot[self.zoom]
    cur_dot = []
    rad = int(self.zoom * DOT_MULT)
    for i in range(int(rad * 2)):
      cur_dot.append([0.] * int(rad * 2))
    for y in range(0, int(rad * 2)):
      for x in range(0, int(rad * 2)):
        y_adj = math.pow((y - rad), 2) # * len(point.checkin_list)
        x_adj = math.pow((x - rad), 2) # * len(point.checkin_list)
        pt_rad = math.sqrt(y_adj + x_adj)
        temp_rad = rad  #* len(point.checkin_list)
        if pt_rad > temp_rad:
          cur_dot[y][x] = 0.
          continue
        cur_dot[y][x] = self.calc_point(rad, pt_rad, len(point.checkin_list))
    y_off = int(math.ceil((-1 * self.northwest_ll[0] + point.location.lat) / self.latlng_diff[0] * 256. - len(cur_dot) / 2))
    x_off = int(math.ceil((-1 * self.northwest_ll[1] + point.location.lon) / self.latlng_diff[1] * 256. - len(cur_dot[0]) / 2))
    return cur_dot, x_off, y_off

  def __create_empty_space(self):
    space = []
    for i in range(256):
      space.append( [0.] * 256 )
    return space

  def image_out(self):
    if self.tile_img:
      self.tile_dump = self.tile_img.dump()

    if self.tile_dump:
      return self.tile_dump
    else:
      raise Exception("Failure in generation of image.")

class CustomTile(BasicTile):
  def __init__(self, user, zoom, lat_north, lng_west, offset_x_px, offset_y_px):
    self.zoom = zoom
    self.decay = 0.5
    #dot_radius = int(math.ceil(len(dot[self.zoom]) / 2))
    dot_radius = int(math.ceil((self.zoom + 1) * DOT_MULT)) #TODO double check that this is + 1 - because range started from 1 in old dot array?!

    # convert to pixel first so we can factor in the dot radius and get the tile bounds
    northwest_px = gmerc.ll2px(lat_north, lng_west, zoom)

    self.northwest_ll_buffered = gmerc.px2ll(northwest_px[0] + offset_x_px       - dot_radius, northwest_px[1] + offset_y_px       - dot_radius, zoom)
    self.northwest_ll          = gmerc.px2ll(northwest_px[0] + offset_x_px                   , northwest_px[1] + offset_y_px                   , zoom)

    self.southeast_ll_buffered = gmerc.px2ll(northwest_px[0] + offset_x_px + 256 + dot_radius, northwest_px[1] + offset_y_px + 256 + dot_radius, zoom)
    self.southeast_ll          = gmerc.px2ll(northwest_px[0] + offset_x_px + 256             , northwest_px[1] + offset_y_px + 256             , zoom) # THIS IS IMPORTANT TO PROPERLY CALC latlng_diff

    self.latlng_diff_buffered = [ self.southeast_ll_buffered[0] - self.northwest_ll_buffered[0], self.southeast_ll_buffered[1] - self.northwest_ll_buffered[1]]
    self.latlng_diff          = [ self.southeast_ll[0]          - self.northwest_ll[0]         , self.southeast_ll[1]          - self.northwest_ll[1]]

    BasicTile.__init__(self, user, self.northwest_ll_buffered[0], self.northwest_ll_buffered[1], self.latlng_diff_buffered[0], self.latlng_diff_buffered[1])


class GoogleTile(BasicTile):
  def __init__(self, user, zoom, x_tile, y_tile):
    self.zoom = zoom
    self.decay = 0.5
    #dot_radius = int(math.ceil(len(dot[self.zoom]) / 2))
    dot_radius = int(math.ceil((self.zoom + 1) * DOT_MULT))

    self.northwest_ll_buffered = gmerc.px2ll((x_tile    ) * 256 - dot_radius, (y_tile    ) * 256 - dot_radius, zoom)
    self.northwest_ll          = gmerc.px2ll((x_tile    ) * 256             , (y_tile    ) * 256             , zoom)

    self.southeast_ll_buffered = gmerc.px2ll((x_tile + 1) * 256 + dot_radius, (y_tile + 1) * 256 + dot_radius, zoom) #TODO fix this in case we're at the edge of the map!
    self.southeast_ll          = gmerc.px2ll((x_tile + 1) * 256             , (y_tile + 1) * 256             , zoom)

    # calculate the real values for these without the offsets, otherwise it messes up the get_dot calculations
    self.latlng_diff_buffered = [ self.southeast_ll_buffered[0] - self.northwest_ll_buffered[0], self.southeast_ll_buffered[1] - self.northwest_ll_buffered[1]]
    self.latlng_diff          = [ self.southeast_ll[0]          - self.northwest_ll[0]         , self.southeast_ll[1]          - self.northwest_ll[1]]

    BasicTile.__init__(self, user, self.northwest_ll_buffered[0], self.northwest_ll_buffered[1], self.latlng_diff_buffered[0], self.latlng_diff_buffered[1])