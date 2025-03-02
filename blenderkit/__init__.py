# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "BlenderKit Online Asset Library",
    "author": "Vilem Duha, Petr Dlouhy",
    "version": (3, 0, 0),
    "blender": (2, 93, 0),
    "location": "View3D > Properties > BlenderKit",
    "description": "Online BlenderKit library (materials, models, brushes and more). Connects to the internet.",
    "warning": "",
    "doc_url": "{BLENDER_MANUAL_URL}/addons/3d_view/blenderkit.html",
    "category": "3D View",
}

if "bpy" in locals():
    from importlib import reload

    # alphabetically sorted all add-on modules since reload only happens from __init__.
    # modules with _bg are used for background computations in separate blender instance and that's why they don't need reload.

    append_link = reload(append_link)
    asset_bar_op = reload(asset_bar_op)
    asset_inspector = reload(asset_inspector)
    autothumb = reload(autothumb)
    bg_blender = reload(bg_blender)
    bkit_oauth = reload(bkit_oauth)
    categories = reload(categories)
    colors = reload(colors)
    download = reload(download)
    icons = reload(icons)
    image_utils = reload(image_utils)
    oauth = reload(oauth)
    overrides = reload(overrides)
    paths = reload(paths)
    ratings = reload(ratings)
    ratings_utils = reload(ratings_utils)
    resolutions = reload(resolutions)
    search = reload(search)
    tasks_queue = reload(tasks_queue)
    ui = reload(ui)
    ui_bgl = reload(ui_bgl)
    ui_panels = reload(ui_panels)
    upload = reload(upload)
    upload_bg = reload(upload_bg)
    utils = reload(utils)

    bl_ui_label = reload(bl_ui_label)
    bl_ui_button = reload(bl_ui_button)
    # bl_ui_checkbox = reload(bl_ui_checkbox)
    # bl_ui_slider = reload(bl_ui_slider)
    # bl_ui_up_down = reload(bl_ui_up_down)
    bl_ui_drag_panel = reload(bl_ui_drag_panel)
    bl_ui_draw_op = reload(bl_ui_draw_op)
    # bl_ui_textbox = reload(bl_ui_textbox)

else:
    from blenderkit import append_link
    from blenderkit import asset_bar_op
    from blenderkit import asset_inspector
    from blenderkit import autothumb
    from blenderkit import bg_blender
    from blenderkit import bkit_oauth
    from blenderkit import categories
    from blenderkit import colors
    from blenderkit import download
    from blenderkit import icons
    from blenderkit import image_utils
    from blenderkit import oauth
    from blenderkit import overrides
    from blenderkit import paths
    from blenderkit import ratings
    from blenderkit import ratings_utils
    from blenderkit import resolutions
    from blenderkit import search
    from blenderkit import tasks_queue
    from blenderkit import ui
    from blenderkit import ui_bgl
    from blenderkit import ui_panels
    from blenderkit import upload
    from blenderkit import upload_bg
    from blenderkit import utils

    from blenderkit.bl_ui_widgets import bl_ui_label
    from blenderkit.bl_ui_widgets import bl_ui_button
    # from blenderkit.bl_ui_widgets import bl_ui_checkbox
    # from blenderkit.bl_ui_widgets import bl_ui_slider
    # from blenderkit.bl_ui_widgets import bl_ui_up_down
    from blenderkit.bl_ui_widgets import bl_ui_drag_panel
    from blenderkit.bl_ui_widgets import bl_ui_draw_op
    # from blenderkit.bl_ui_widgets import bl_ui_textbox

import os
import math
import time
import logging
import bpy
import pathlib

log = logging.getLogger(__name__)

from bpy.app.handlers import persistent
import bpy.utils.previews
import mathutils
from mathutils import Vector
from bpy.props import (
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    StringProperty,
    EnumProperty,
    BoolProperty,
    PointerProperty,
)
from bpy.types import (
    Operator,
    Panel,
    AddonPreferences,
    PropertyGroup,
)


# logging.basicConfig(filename = 'blenderkit.log', level = logging.INFO,
#                     format = '	%(asctime)s:%(filename)s:%(funcName)s:%(lineno)d:%(message)s')


@persistent
def scene_load(context):
    ui_props = bpy.context.scene.blenderkitUI
    ui_props.assetbar_on = False
    ui_props.turn_off = False
    preferences = bpy.context.preferences.addons['blenderkit'].preferences
    preferences.login_attempt = False


@bpy.app.handlers.persistent
def check_timers_timer():
    ''' checks if all timers are registered regularly. Prevents possible bugs from stopping the addon.'''
    if not bpy.app.timers.is_registered(search.search_timer):
        bpy.app.timers.register(search.search_timer)
    if not bpy.app.timers.is_registered(download.download_timer):
        bpy.app.timers.register(download.download_timer)
    if not (bpy.app.timers.is_registered(tasks_queue.queue_worker)):
        bpy.app.timers.register(tasks_queue.queue_worker)
    if not bpy.app.timers.is_registered(bg_blender.bg_update):
        bpy.app.timers.register(bg_blender.bg_update)
    return 5.0


conditions = (
    ('UNSPECIFIED', 'Unspecified', ""),
    ('NEW', 'New', 'Shiny new item'),
    ('USED', 'Used', 'Casually used item'),
    ('OLD', 'Old', 'Old item'),
    ('DESOLATE', 'Desolate', 'Desolate item - dusty & rusty'),
)
model_styles = (
    ('REALISTIC', 'Realistic', "Photo realistic model"),
    ('PAINTERLY', 'Painterly', 'Hand painted with visible strokes'),
    ('LOWPOLY', 'Lowpoly', "Lowpoly art -don't mix up with polycount!"),
    ('ANIME', 'Anime', 'Anime style'),
    ('2D_VECTOR', '2D Vector', '2D vector'),
    ('3D_GRAPHICS', '3D Graphics', '3D graphics'),
    ('OTHER', 'Other', 'Other styles'),
)
search_model_styles = (
    ('REALISTIC', 'Realistic', "Photo realistic model"),
    ('PAINTERLY', 'Painterly', 'Hand painted with visible strokes'),
    ('LOWPOLY', 'Lowpoly', "Lowpoly art -don't mix up with polycount!"),
    ('ANIME', 'Anime', 'Anime style'),
    ('2D_VECTOR', '2D Vector', '2D vector'),
    ('3D_GRAPHICS', '3D Graphics', '3D graphics'),
    ('OTHER', 'Other', 'Other Style'),
    ('ANY', 'Any', 'Any Style'),
)
material_styles = (
    ('REALISTIC', 'Realistic', "Photo realistic model"),
    ('NPR', 'Non photorealistic', 'Hand painted with visible strokes'),
    ('OTHER', 'Other', 'Other style'),
)
search_material_styles = (
    ('REALISTIC', 'Realistic', "Photo realistic model"),
    ('NPR', 'Non photorealistic', 'Hand painted with visible strokes'),
    ('ANY', 'Any', 'Any'),
)
engines = (
    ('CYCLES', 'Cycles', 'Blender Cycles'),
    ('EEVEE', 'Eevee', 'Blender eevee renderer'),
    ('OCTANE', 'Octane', 'Octane render enginge'),
    ('ARNOLD', 'Arnold', 'Arnold render engine'),
    ('V-RAY', 'V-Ray', 'V-Ray renderer'),
    ('UNREAL', 'Unreal', 'Unreal engine'),
    ('UNITY', 'Unity', 'Unity engine'),
    ('GODOT', 'Godot', 'Godot engine'),
    ('3D-PRINT', '3D printer', 'object can be 3D printed'),
    ('OTHER', 'Other', 'any other engine'),
    ('NONE', 'None', 'no more engine block'),
)
pbr_types = (
    ('METALLIC', 'Metallic-Roughness', 'Metallic/Roughness PBR material type'),
    ('SPECULAR', 'Specular  Glossy', ''),
)

mesh_poly_types = (
    ('QUAD', 'quad', ''),
    ('QUAD_DOMINANT', 'quad_dominant', ''),
    ('TRI_DOMINANT', 'tri_dominant', ''),
    ('TRI', 'tri', ''),
    ('NGON', 'ngon_dominant', ''),
    ('OTHER', 'other', ''),
)







def udate_down_up(self, context):
    """Perform a search if results are empty."""
    s = context.scene
    wm = bpy.context.window_manager
    props = s.blenderkitUI
    if wm.get('search results') == None and props.down_up == 'SEARCH':
        search.search()


def switch_search_results(self, context):
    s = bpy.context.scene
    wm = bpy.context.window_manager
    props = s.blenderkitUI
    if props.asset_type == 'MODEL':
        wm['search results'] = wm.get('bkit model search')
        wm['search results orig'] = wm.get('bkit model search orig')
    elif props.asset_type == 'SCENE':
        wm['search results'] = wm.get('bkit scene search')
        wm['search results orig'] = wm.get('bkit scene search orig')
    elif props.asset_type == 'HDR':
        wm['search results'] = wm.get('bkit hdr search')
        wm['search results orig'] = wm.get('bkit hdr search orig')
    elif props.asset_type == 'MATERIAL':
        wm['search results'] = wm.get('bkit material search')
        wm['search results orig'] = wm.get('bkit material search orig')
    elif props.asset_type == 'TEXTURE':
        wm['search results'] = wm.get('bkit texture search')
        wm['search results orig'] = wm.get('bkit texture search orig')
    elif props.asset_type == 'BRUSH':
        wm['search results'] = wm.get('bkit brush search')
        wm['search results orig'] = wm.get('bkit brush search orig')
        if not (context.sculpt_object or context.image_paint_object):
            ui.add_report(
                'Switch to paint or sculpt mode to search in BlenderKit brushes.')

    search.load_previews()
    if wm['search results'] == None and props.down_up == 'SEARCH':
        search.search()


def asset_type_callback(self, context):
    '''
    Returns
    items for Enum property, depending on the down_up property - BlenderKit is either in search or in upload mode.

    '''
    user_preferences = bpy.context.preferences.addons['blenderkit'].preferences

    if self.down_up == 'SEARCH':
        items = (
            ('MODEL', 'Models', 'Find models', 'OBJECT_DATAMODE', 0),
            ('MATERIAL', 'Materials', 'Find materials', 'MATERIAL', 2),
            # ('TEXTURE', 'Texture', 'Browse textures', 'TEXTURE', 3),
            ('SCENE', 'Scenes', 'Find scenes', 'SCENE_DATA', 3),
            ('HDR', 'HDRs', 'Find HDRs', 'WORLD', 4),
            ('BRUSH', 'Brushes', 'Find brushes', 'BRUSH_DATA', 5)
        )
    else:
        items = (
            ('MODEL', 'Model', 'Upload a model', 'OBJECT_DATAMODE', 0),
            # ('SCENE', 'SCENE', 'Browse scenes', 'SCENE_DATA', 1),
            ('MATERIAL', 'Material', 'Upload a material', 'MATERIAL', 2),
            # ('TEXTURE', 'Texture', 'Browse textures', 'TEXTURE', 3),
            ('SCENE', 'Scene', 'Upload a scene', 'SCENE_DATA', 3),
            ('HDR', 'HDR', 'Upload a HDR', 'WORLD', 4),
            ('BRUSH', 'Brush', 'Upload a brush', 'BRUSH_DATA', 5)
        )

    return items


def run_drag_drop_update(self, context):
    if self.drag_init_button:
        ui_props = bpy.context.scene.blenderkitUI
        # ctx = utils.get_fake_context(bpy.context)

        bpy.ops.view3d.close_popup_button('INVOKE_DEFAULT')
        bpy.ops.view3d.asset_drag_drop('INVOKE_DEFAULT', asset_search_index=ui_props.active_index + ui_props.scrolloffset)

        self.drag_init_button = False


class BlenderKitUIProps(PropertyGroup):

    down_up: EnumProperty(
        name="Download vs Upload",
        items=(
            ('SEARCH', 'Search', 'Activate searching', 'VIEWZOOM', 0),
            ('UPLOAD', 'Upload', 'Activate uploading', 'COPYDOWN', 1),
            # ('RATING', 'Rating', 'Activate rating', 'SOLO_ON', 2)
        ),
        description="BlenderKit",
        default="SEARCH",
        update=udate_down_up
    )
    asset_type: EnumProperty(
        name=" ",
        items=asset_type_callback,
        description="",
        default=None,
        update=switch_search_results
    )

    asset_type_fold:  BoolProperty(name="Expand asset types", default=False)
    # these aren't actually used ( by now, seems to better use globals in UI module:
    draw_tooltip: BoolProperty(name="Draw Tooltip", default=False)
    addon_update: BoolProperty(name="Should Update Addon", default=False)
    tooltip: StringProperty(
        name="Tooltip",
        description="asset preview info",
        default="")

    ui_scale = 1

    thumb_size_def = 96
    margin_def = 0

    thumb_size: IntProperty(name="Thumbnail Size", default=thumb_size_def, min=-1, max=256)

    margin: IntProperty(name="Margin", default=margin_def, min=-1, max=256)
    highlight_margin: IntProperty(name="Highlight Margin", default=int(margin_def / 2), min=-10, max=256)

    bar_height: IntProperty(name="Bar Height", default=thumb_size_def + 2 * margin_def, min=-1, max=2048)
    bar_x_offset: IntProperty(name="Bar X Offset", default=20, min=0, max=5000)
    bar_y_offset: IntProperty(name="Bar Y Offset", default=80, min=0, max=5000)

    bar_x: IntProperty(name="Bar X", default=100, min=0, max=5000)
    bar_y: IntProperty(name="Bar Y", default=100, min=50, max=5000)
    bar_end: IntProperty(name="Bar End", default=100, min=0, max=5000)
    bar_width: IntProperty(name="Bar Width", default=100, min=0, max=5000)

    wcount: IntProperty(name="Width Count", default=10, min=0, max=5000)
    hcount: IntProperty(name="Rows", default=5, min=0, max=5000)

    reports_y: IntProperty(name="Reports Y", default=5, min=0, max=5000)
    reports_x: IntProperty(name="Reports X", default=5, min=0, max=5000)

    assetbar_on: BoolProperty(name="Assetbar On", default=False)
    turn_off: BoolProperty(name="Turn Off", default=False)

    mouse_x: IntProperty(name="Mouse X", default=0)
    mouse_y: IntProperty(name="Mouse Y", default=0)

    active_index: IntProperty(name="Active Index", default=-3)
    scrolloffset: IntProperty(name="Scroll Offset", default=0)
    drawoffset: IntProperty(name="Draw Offset", default=0)

    dragging: BoolProperty(name="Dragging", default=False)
    drag_init: BoolProperty(name="Drag Initialisation", default=False)
    drag_init_button: BoolProperty(name="Drag Initialisation from button",
                                   default=False,
                                   description="Click or drag into scene for download",
                                   update = run_drag_drop_update)
    drag_length: IntProperty(name="Drag length", default=0)
    draw_drag_image: BoolProperty(name="Draw Drag Image", default=False)
    draw_snapped_bounds: BoolProperty(name="Draw Snapped Bounds", default=False)

    snapped_location: FloatVectorProperty(name="Snapped Location", default=(0, 0, 0))
    snapped_bbox_min: FloatVectorProperty(name="Snapped Bbox Min", default=(0, 0, 0))
    snapped_bbox_max: FloatVectorProperty(name="Snapped Bbox Max", default=(0, 0, 0))
    snapped_normal: FloatVectorProperty(name="Snapped Normal", default=(0, 0, 0))

    snapped_rotation: FloatVectorProperty(name="Snapped Rotation", default=(0, 0, 0), subtype='QUATERNION')

    has_hit: BoolProperty(name="has_hit", default=False)
    thumbnail_image = StringProperty(
        name="Thumbnail Image",
        description="",
        default=paths.get_addon_thumbnail_path('thumbnail_notready.jpg'))

    #### rating UI props
    rating_ui_scale = ui_scale

    rating_button_on: BoolProperty(name="Rating Button On", default=True)
    rating_menu_on: BoolProperty(name="Rating Menu On", default=False)
    rating_on: BoolProperty(name="Rating on", default=True)

    rating_button_width: IntProperty(name="Rating Button Width", default=50 * ui_scale)
    rating_button_height: IntProperty(name="Rating Button Height", default=50 * ui_scale)

    rating_x: IntProperty(name="Rating UI X", default=10)
    rating_y: IntProperty(name="Rating UI Y", default=10)

    rating_ui_width: IntProperty(name="Rating UI Width", default=rating_ui_scale * 600)
    rating_ui_height: IntProperty(name="Rating UI Heightt", default=rating_ui_scale * 256)

    quality_stars_x: IntProperty(name="Rating UI Stars X", default=rating_ui_scale * 90)
    quality_stars_y: IntProperty(name="Rating UI Stars Y", default=rating_ui_scale * 190)

    star_size: IntProperty(name="Star Size", default=rating_ui_scale * 50)

    workhours_bar_slider_size: IntProperty(name="Workhours Bar Slider Size", default=rating_ui_scale * 30)

    workhours_bar_x: IntProperty(name="Workhours Bar X", default=rating_ui_scale * (100 - 15))
    workhours_bar_y: IntProperty(name="Workhours Bar Y", default=rating_ui_scale * (45 - 15))

    workhours_bar_x_max: IntProperty(name="Workhours Bar X Max", default=rating_ui_scale * (480 - 15))

    dragging_rating: BoolProperty(name="Dragging Rating", default=False)
    dragging_rating_quality: BoolProperty(name="Dragging Rating Quality", default=False)
    dragging_rating_work_hours: BoolProperty(name="Dragging Rating Work Hours", default=False)
    last_rating_time: FloatProperty(name="Last Rating Time", default=0.0)

    hdr_upload_image: PointerProperty(name='Upload HDR',
                                      type=bpy.types.Image,
                                      description='Pick an image to upload')

    # StringProperty(
    # name="Upload HDR",
    # description="Active HDR image to upload",
    # default="")


def search_procedural_update(self, context):
    if self.search_procedural in ('PROCEDURAL', 'BOTH'):
        self.search_texture_resolution = False
    search.search_update(self, context)


class BlenderKitCommonSearchProps(object):
    # STATES
    is_searching: BoolProperty(name="Searching", description="search is currently running (internal)", default=False)
    is_downloading: BoolProperty(name="Downloading", description="download is currently running (internal)",
                                 default=False)
    search_done: BoolProperty(name="Search Completed", description="at least one search did run (internal)",
                              default=False)
    own_only: BoolProperty(name="My Assets Only", description="Search only for your assets",
                           default=False, update=search.search_update)
    use_filters: BoolProperty(name="Filters are on", description="some filters are used",
                                  default=False)

    search_error: BoolProperty(name="Search Error", description="last search had an error", default=False)
    report: StringProperty(
        name="Report",
        description="errors and messages",
        default="")

    # TEXTURE RESOLUTION
    search_texture_resolution: BoolProperty(name="Texture Resolution",
                                            description="Limit texture resolutions",
                                            default=False,
                                            update=search.search_update,
                                            )
    search_texture_resolution_min: IntProperty(name="Min Texture Resolution",
                                               description="Minimum texture resolution",
                                               default=256,
                                               min=0,
                                               max=32768,
                                               update=search.search_update,
                                               )

    search_texture_resolution_max: IntProperty(name="Max Texture Resolution",
                                               description="Maximum texture resolution",
                                               default=4096,
                                               min=0,
                                               max=32768,
                                               update=search.search_update,
                                               )

    # file_size
    search_file_size: BoolProperty(name="File Size",
                                   description="Limit file sizes",
                                   default=False,
                                   update=search.search_update,
                                   )
    search_file_size_min: IntProperty(name="Min File Size",
                                      description="Minimum file size",
                                      default=0,
                                      min=0,
                                      max=2000,
                                      update=search.search_update,
                                      )

    search_file_size_max: IntProperty(name="Max File Size",
                                      description="Maximum file size",
                                      default=500,
                                      min=0,
                                      max=2000,
                                      update=search.search_update,
                                      )

    search_procedural: EnumProperty(
        items=(
            ('BOTH', 'Both', ''),
            ('PROCEDURAL', 'Procedural', ''),
            ('TEXTURE_BASED', 'Texture based', ''),

        ),
        default='BOTH',
        description='Search only procedural/texture based assets',
        update=search_procedural_update
    )

    search_verification_status: EnumProperty(
        name="Verification status",
        description="Search by verification status",
        items=
        (
            ('ALL', 'All', 'All'),
            ('UPLOADING', 'Uploading', 'Uploading'),
            ('UPLOADED', 'Uploaded', 'Uploaded'),
            ('READY', 'Ready for V.', 'Ready for validation (deprecated since 2.8)'),
            ('VALIDATED', 'Validated', 'Validated'),
            ('ON_HOLD', 'On Hold', 'On Hold'),
            ('REJECTED', 'Rejected', 'Rejected'),
            ('DELETED', 'Deleted', 'Deleted'),
        ),
        default='ALL',
        update=search.search_update,
    )

    # resolution download/import settings
    resolution: EnumProperty(
        name="Max resolution",
        description="Cap texture sizes in the file to this resolution",
        items=
        (
            # ('256', '256x256', ''),
            ('512', '512x512', ''),
            ('1024', '1024x1024', ''),
            ('2048', '2048x2048', ''),
            ('4096', '4096x4096', ''),
            ('8192', '8192x8192', ''),
            ('ORIGINAL', 'ORIGINAL FILE', ''),

        ),
        default='1024',
    )
    free_only: BoolProperty(name="Free first", description="Show free models first",
                            default=False, update=search.search_update)

    unpack_files: BoolProperty(name="Unpack Files",
                               description="Unpack files after download",
                               default=True
                               )

    unrated_only: BoolProperty(name="Unrated only", description="Show only unrated models",
                               default=False, update=search.search_update)
    quality_limit: IntProperty(name="Quality limit",
                               description = 'Only show assets with a higher quality',
                               default=0, min=0, max=10, update=search.search_update)



def name_update(self, context):
    ''' checks for name change, because it decides if whole asset has to be re-uploaded. Name is stored in the blend file
    and that's the reason.'''
    utils.name_update(self)


def update_free(self, context):
    if self.is_free == 'FULL':
        self.is_free = 'FREE'
        ui_panels.ui_message(title="All BlenderKit materials are free",
                             message="Any material uploaded to BlenderKit is free." \
                                     " However, it can still earn money for the author," \
                                     " based on our fair share system. " \
                                     "Part of subscription is sent to artists based on usage by paying users.\n")

# common_upload_props = [
#     {
#         'identifier':'id',
#         'name':"Asset Version Id",
#         'type':'StringProperty',
#         'description':'Unique name of the asset version(hidden)',
#         'default':''
# }
# {
#         'identifier':'id',
#         'name':"Asset Version Id",
#         'type':'StringProperty',
#         'description':'Unique name of the asset version(hidden)',
#         'default':''
# }
# ]




class BlenderKitCommonUploadProps(object):
    # for p in common_upload_props:
    #     exec(f"{p['identifier']}: {p['type']}(name='{p['name']}',description='{p['description']}',default='{p['default']}')")

    id: StringProperty(
        name="Asset Version Id",
        description="Unique name of the asset version(hidden)",
        default="")
    asset_base_id: StringProperty(
        name="Asset Base Id",
        description="Unique name of the asset (hidden)",
        default="")
    name: StringProperty(
        name="Name",
        description="Main name of the asset",
        default="",
        update=name_update
    )
    # this is to store name for purpose of checking if name has changed.
    name_old: StringProperty(
        name="Old Name",
        description="Old name of the asset",
        default="",
    )

    description: StringProperty(
        name="Description",
        description="Description of the asset",
        default="")
    tags: StringProperty(
        name="Tags",
        description="List of tags, separated by commas (optional)",
        default="",
        update=utils.update_tags
    )

    name_changed: BoolProperty(name="Name Changed",
                               description="Name has changed, the asset has to be re-uploaded with all data",
                               default=False)

    pbr: BoolProperty(name="Pure PBR Compatible",
                      description="Is compatible with PBR standard. This means only image textures are used with no"
                                  " procedurals and no color correction, only principled shader is used",
                      default=False)

    pbr_type: EnumProperty(
        name="PBR Type",
        items=pbr_types,
        description="PBR type",
        default="METALLIC",
    )
    license: EnumProperty(
        items=upload.licenses,
        default='royalty_free',
        description='License. Please read our help for choosing the right licenses',
    )

    is_private: EnumProperty(
        name="Thumbnail Style",
        items=(
            ('PRIVATE', 'Private', ""),
            ('PUBLIC', 'Public', "")
        ),
        description="Public assets go into the validation process. \n"
                    "Validated assets are visible to all users.\n"
                    "Private assets are limited by your plan quota\n"
                    "State",
        default="PUBLIC",
    )

    is_procedural: BoolProperty(name="Procedural",
                                description="Asset is procedural - has no texture",
                                default=True
                                )
    node_count: IntProperty(name="Node count", description="Total nodes in the asset", default=0)
    texture_count: IntProperty(name="Texture count", description="Total texture count in asset", default=0)
    total_megapixels: IntProperty(name="Megapixels", description="Total megapixels of texture", default=0)

    # is_private: BoolProperty(name="Asset is Private",
    #                       description="If not marked private, your asset will go into the validation process automatically\n"
    #                                   "Private assets are limited by quota",
    #                       default=False)

    is_free: EnumProperty(
        name="Thumbnail Style",
        items=(
            ('FULL', 'Full', "Your asset will be only available for subscribers"),
            ('FREE', 'Free', "You consent you want to release this asset as free for everyone")
        ),
        description="Assets can be in Free or in Full plan. Also free assets generate credits",
        default="FULL",
    )

    uploading: BoolProperty(name="Uploading",
                            description="True when background process is running",
                            default=False,
                            update=autothumb.update_upload_material_preview)
    upload_state: StringProperty(
        name="State Of Upload",
        description="bg process reports for upload",
        default='')

    has_thumbnail: BoolProperty(name="Has Thumbnail", description="True when thumbnail was checked and loaded",
                                default=False)

    thumbnail_generating_state: StringProperty(
        name="Thumbnail Generating State",
        description="bg process reports for thumbnail generation",
        default='Please add thumbnail(jpg or png, at least 512x512)')

    report: StringProperty(
        name="Missing Upload Properties",
        description="used to write down what's missing",
        default='')

    category: EnumProperty(
        name="Category",
        description="main category to put into",
        items=categories.get_category_enums,
        update=categories.update_category_enums
    )
    subcategory: EnumProperty(
        name="Subcategory",
        description="Subcategory to put into",
        items=categories.get_subcategory_enums,
        update=categories.update_subcategory_enums
    )
    subcategory1: EnumProperty(
        name="Subcategory lvl2",
        description="Subcategory to put into",
        items=categories.get_subcategory1_enums
    )


class BlenderKitRatingProps(PropertyGroup):
    rating_quality: IntProperty(name="Quality",
                                description="quality of the material",
                                default=0,
                                min=-1, max=10,
                                update=ratings_utils.update_ratings_quality)

    # the following enum is only to ease interaction - enums support 'drag over' and enable to draw the stars easily.
    rating_quality_ui: EnumProperty(name='rating_quality_ui',
                                    items=ratings_utils.stars_enum_callback,
                                    description='Rating stars 0 - 10',
                                    default=None,
                                    update=ratings_utils.update_quality_ui,
                                    )

    rating_work_hours: FloatProperty(name="Work Hours",
                                     description="How many hours did this work take?",
                                     default=0.00,
                                     min=0.0, max=150, update=ratings_utils.update_ratings_work_hours
                                     )

    # rating_complexity: IntProperty(name="Complexity",
    #                                description="Complexity is a number estimating how much work was spent on the asset.aaa",
    #                                default=0, min=0, max=10)
    # rating_virtual_price: FloatProperty(name="Virtual Price",
    #                                     description="How much would you pay for this object if buing it?",
    #                                     default=0, min=0, max=10000)
    rating_problems: StringProperty(
        name="Problems",
        description="Problems found/ why did you take points down - this will be available for the author"
                    " As short as possible",
        default="",
    )
    rating_compliments: StringProperty(
        name="Compliments",
        description="Comliments - let the author know you like his work! "
                    " As short as possible",
        default="",
    )


class BlenderKitMaterialSearchProps(PropertyGroup, BlenderKitCommonSearchProps):
    search_keywords: StringProperty(
        name="Search",
        description="Search for these keywords",
        default="",
        update=search.search_update
    )
    search_style: EnumProperty(
        name="Style",
        items=search_material_styles,
        description="Style of material",
        default="ANY",
        update=search.search_update,
    )
    search_style_other: StringProperty(
        name="Style Other",
        description="Style not in the list",
        default="",
        update=search.search_update,
    )
    search_engine: EnumProperty(
        name='Engine',
        items=engines,
        default='NONE',
        description='Output engine',
        update=search.search_update,
    )
    search_engine_other: StringProperty(
        name="Engine",
        description="engine not specified by addon",
        default="",
        update=search.search_update,
    )
    append_method: EnumProperty(
        name="Import Method",
        items=(
            ('LINK', 'Link', "Link Material - will be in external file and can't be directly edited"),
            ('APPEND', 'Append', 'Append if you need to edit the material'),
        ),
        description="Appended materials are editable in your scene. Linked assets are saved in original files, "
                    "aren't editable directly, but also don't increase your file size",
        default="APPEND"
    )
    automap: BoolProperty(name="Auto-Map",
                          description="reset object texture space and also add automatically a cube mapped UV "
                                      "to the object. \n this allows most materials to apply instantly to any mesh",
                          default=True)


class BlenderKitMaterialUploadProps(PropertyGroup, BlenderKitCommonUploadProps):
    style: EnumProperty(
        name="Style",
        items=material_styles,
        description="Style of material",
        default="REALISTIC",
    )
    style_other: StringProperty(
        name="Style Other",
        description="Style not in the list",
        default="",
    )
    engine: EnumProperty(
        name='Engine',
        items=engines,
        default='CYCLES',
        description='Output engine',
    )
    engine_other: StringProperty(
        name="Engine Other",
        description="engine not specified by addon",
        default="",
    )

    shaders: StringProperty(
        name="Shaders Used",
        description="shaders used in asset, autofilled",
        default="",
    )

    is_free: EnumProperty(
        name="Thumbnail Style",
        items=(
            ('FULL', 'Full', "Your asset will be only available for subscribers."),
            ('FREE', 'Free', "You consent you want to release this asset as free for everyone.")
        ),
        description="Assets can be in Free or in Full plan. Also free assets generate credits. \n"
                    "All BlenderKit materials are free",
        default="FREE",
        update=update_free
    )



    uv: BoolProperty(name="Needs UV", description="needs an UV set", default=False)
    # printable_3d : BoolProperty( name = "3d printable", description = "can be 3d printed", default = False)
    animated: BoolProperty(name="Animated", description="is animated", default=False)
    texture_resolution_min: IntProperty(name="Texture Resolution Min", description="texture resolution minimum",
                                        default=0)
    texture_resolution_max: IntProperty(name="Texture Resolution Max", description="texture resolution maximum",
                                        default=0)

    texture_size_meters: FloatProperty(name="Texture Size in Meters", description="Size of texture in real world units",
                                       default=1.0, min=0)

    thumbnail_scale: FloatProperty(name="Thumbnail Object Size",
                                   description="Size of material preview object in meters."
                                               "Change for materials that look better at sizes different than 1m",
                                   default=1, min=0.00001, max=10)
    thumbnail_background: BoolProperty(name="Thumbnail Background (for Glass only)",
                                       description="For refractive materials, you might need a background.\n"
                                                   "Don't use for other types of materials.\n"
                                                   "Transparent background is preferred",
                                       default=False)
    thumbnail_background_lightness: FloatProperty(name="Thumbnail Background Lightness",
                                                  description="Set to make your material stand out with enough contrast",
                                                  default=.9,
                                                  min=0.00001, max=1)
    thumbnail_samples: IntProperty(name="Cycles Samples",
                                   description="Cycles samples", default=100,
                                   min=5, max=5000)
    thumbnail_denoising: BoolProperty(name="Use Denoising",
                                      description="Use denoising", default=True)
    adaptive_subdivision: BoolProperty(name="Adaptive Subdivide",
                                       description="Use adaptive displacement subdivision", default=False)

    thumbnail_resolution: EnumProperty(
        name="Resolution",
        items=autothumb.thumbnail_resolutions,
        description="Thumbnail resolution",
        default="1024",
    )

    thumbnail_generator_type: EnumProperty(
        name="Thumbnail Style",
        items=(
            ('BALL', 'Ball', ""),
            ('BALL_COMPLEX', 'Ball complex', 'Complex ball to highlight edgewear or material thickness'),
            ('FLUID', 'Fluid', 'Fluid'),
            ('CLOTH', 'Cloth', 'Cloth'),
            ('HAIR', 'Hair', 'Hair  ')
        ),
        description="Style of asset",
        default="BALL",
    )

    thumbnail: StringProperty(
        name="Thumbnail",
        description="Thumbnail path - 512x512 .jpg image, rendered with cycles.\n"
                    "Only standard BlenderKit previews will be accepted.\n"
                    "Only exception are special effects like fire or similar",
        subtype='FILE_PATH',
        default="",
        update=autothumb.update_upload_material_preview)

    is_generating_thumbnail: BoolProperty(name="Generating Thumbnail",
                                          description="True when background process is running", default=False,
                                          update=autothumb.update_upload_material_preview)


class BlenderKitTextureUploadProps(PropertyGroup, BlenderKitCommonUploadProps):
    style: EnumProperty(
        name="Style",
        items=material_styles,
        description="Style of texture",
        default="REALISTIC",
    )
    style_other: StringProperty(
        name="Style Other",
        description="Style not in the list",
        default="",
    )

    pbr: BoolProperty(name="PBR Compatible", description="Is compatible with PBR standard", default=False)

    # printable_3d : BoolProperty( name = "3d printable", description = "can be 3d printed", default = False)
    animated: BoolProperty(name="Animated", description="is animated", default=False)
    resolution: IntProperty(name="Texture Resolution", description="texture resolution", default=0)


class BlenderKitBrushSearchProps(PropertyGroup, BlenderKitCommonSearchProps):
    search_keywords: StringProperty(
        name="Search",
        description="Search for these keywords",
        default="",
        update=search.search_update
    )


class BlenderKitHDRUploadProps(PropertyGroup, BlenderKitCommonUploadProps):
    texture_resolution_max: IntProperty(name="Texture Resolution Max", description="texture resolution maximum",
                                        default=0)
    evs_cap: IntProperty(name="EV cap", description="EVs dynamic range",
                                        default=0)
    true_hdr: BoolProperty(name="Real HDR", description="Image has High dynamic range.",default=False)


class BlenderKitBrushUploadProps(PropertyGroup, BlenderKitCommonUploadProps):
    mode: EnumProperty(
        name="Mode",
        items=(
            ("IMAGE", "Texture paint", "Texture brush"),
            ("SCULPT", "Sculpt", "Sculpt brush"),
            ("VERTEX", "Vertex paint", "Vertex paint brush"),
            ("WEIGHT", "Weight paint", "Weight paint brush"),
        ),
        description="Mode where the brush works",
        default="SCULPT",
    )


# upload properties
class BlenderKitModelUploadProps(PropertyGroup, BlenderKitCommonUploadProps):
    style: EnumProperty(
        name="Style",
        items=model_styles,
        description="Style of asset",
        default="REALISTIC",
    )
    style_other: StringProperty(
        name="Style Other",
        description="Style not in the list",
        default="",
    )
    engine: EnumProperty(
        name='Engine',
        items=engines,
        default='CYCLES',
        description='Output engine',
    )

    production_level: EnumProperty(
        name='Production Level',
        items=(
            ('FINISHED', 'Finished', 'Render or animation ready asset'),
            ('TEMPLATE', 'Template', 'Asset intended to help in creation of something else'),
        ),
        default='FINISHED',
        description='Production state of the asset. \n'
                    'Templates should be tools to finish certain tasks, like a thumbnailer scene, \n '
                    'finished mesh topology as start for modelling or others',
    )

    engine_other: StringProperty(
        name="Engine",
        description="engine not specified by addon",
        default="",
    )

    engine1: EnumProperty(
        name='2nd Engine',
        items=engines,
        default='NONE',
        description='Output engine',
    )
    engine2: EnumProperty(
        name='3rd Engine',
        items=engines,
        default='NONE',
        description='Output engine',
    )
    engine3: EnumProperty(
        name='4th Engine',
        items=engines,
        default='NONE',
        description='Output engine',
    )

    manufacturer: StringProperty(
        name="Manufacturer",
        description="Manufacturer, company making a design piece or product. Not you",
        default="",
    )

    designer: StringProperty(
        name="Designer",
        description="Author of the original design piece depicted. Usually not you",
        default="",
    )

    design_collection: StringProperty(
        name="Design Collection",
        description="Fill if this piece is part of a real world design collection",
        default="",
    )

    design_variant: StringProperty(
        name="Variant",
        description="Colour or material variant of the product",
        default="",
    )

    thumbnail: StringProperty(
        name="Thumbnail",
        description="Thumbnail path - 512x512 .jpg\n"
                    "Rendered with cycles",

        subtype='FILE_PATH',
        default="",
        update=autothumb.update_upload_model_preview)

    thumbnail_background_lightness: FloatProperty(name="Thumbnail Background Lightness",
                                                  description="set to make your material stand out", default=1.0,
                                                  min=0.01, max=10)

    thumbnail_angle: EnumProperty(
        name='Thumbnail Angle',
        items=autothumb.thumbnail_angles,
        default='DEFAULT',
        description='thumbnailer angle',
    )

    thumbnail_snap_to: EnumProperty(
        name='Model Snaps To:',
        items=autothumb.thumbnail_snap,
        default='GROUND',
        description='typical placing of the interior. Leave on ground for most objects that respect gravity :)',
    )

    thumbnail_resolution: EnumProperty(
        name="Resolution",
        items=autothumb.thumbnail_resolutions,
        description="Thumbnail resolution",
        default="1024",
    )

    thumbnail_samples: IntProperty(name="Cycles Samples",
                                   description="cycles samples setting", default=100,
                                   min=5, max=5000)
    thumbnail_denoising: BoolProperty(name="Use Denoising",
                                      description="Use denoising", default=True)

    use_design_year: BoolProperty(name="Use Design Year",
                                  description="When this thing came into world for the first time\n"
                                              " e.g. for dinosaur, you set -240 million years ;) ",
                                  default=False)
    design_year: IntProperty(name="Design Year", description="when was this item designed", default=1960)
    # use_age : BoolProperty( name = "use item age", description = "use item age", default = False)
    condition: EnumProperty(
        items=conditions,
        default='UNSPECIFIED',
        description='age of the object',
    )

    adult: BoolProperty(name="Adult Content", description="adult content", default=False)

    work_hours: FloatProperty(name="Work Hours", description="How long did it take you to finish the asset?",
                              default=0.0, min=0.0, max=8760)

    modifiers: StringProperty(
        name="Modifiers Used",
        description="if you need specific modifiers, autofilled",
        default="",
    )

    materials: StringProperty(
        name="Material Names",
        description="names of materials in the file, autofilled",
        default="",
    )
    shaders: StringProperty(
        name="Shaders Used",
        description="shaders used in asset, autofilled",
        default="",
    )

    dimensions: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(0, 0, 0),
    )
    bbox_min: FloatVectorProperty(
        name="Bbox Min",
        description="dimensions of the whole asset hierarchy",
        default=(-.25, -.25, 0),
    )
    bbox_max: FloatVectorProperty(
        name="Bbox Max",
        description="dimensions of the whole asset hierarchy",
        default=(.25, .25, .5),
    )

    texture_resolution_min: IntProperty(name="Texture Resolution Min",
                                        description="texture resolution min, autofilled", default=0)
    texture_resolution_max: IntProperty(name="Texture Resolution Max",
                                        description="texture resolution max, autofilled", default=0)

    pbr: BoolProperty(name="PBR Compatible", description="Is compatible with PBR standard", default=False)

    uv: BoolProperty(name="Has UV", description="has an UV set", default=False)
    # printable_3d : BoolProperty( name = "3d printable", description = "can be 3d printed", default = False)
    animated: BoolProperty(name="Animated", description="is animated", default=False)
    face_count: IntProperty(name="Face count", description="face count, autofilled", default=0)
    face_count_render: IntProperty(name="Render Face Count", description="render face count, autofilled", default=0)

    object_count: IntProperty(name="Number of Objects", description="how many objects are in the asset, autofilled",
                              default=0)
    mesh_poly_type: EnumProperty(
        name='Dominant Poly Type',
        items=mesh_poly_types,
        default='OTHER',
        description='',
    )

    manifold: BoolProperty(name="Manifold", description="asset is manifold, autofilled", default=False)

    rig: BoolProperty(name="Rig", description="asset is rigged, autofilled", default=False)
    simulation: BoolProperty(name="Simulation", description="asset uses simulation, autofilled", default=False)
    '''
    filepath : StringProperty(
            name="Filepath",
            description="file path",
            default="",
            )
    '''

    # THUMBNAIL STATES
    is_generating_thumbnail: BoolProperty(name="Generating Thumbnail",
                                          description="True when background process is running", default=False,
                                          update=autothumb.update_upload_model_preview)

    has_autotags: BoolProperty(name="Has Autotagging Done", description="True when autotagging done", default=False)


class BlenderKitSceneUploadProps(PropertyGroup, BlenderKitCommonUploadProps):
    style: EnumProperty(
        name="Style",
        items=model_styles,
        description="Style of asset",
        default="REALISTIC",
    )
    style_other: StringProperty(
        name="Style Other",
        description="Style not in the list",
        default="",
    )
    engine: EnumProperty(
        name='Engine',
        items=engines,
        default='CYCLES',
        description='Output engine',
    )

    production_level: EnumProperty(
        name='Production Level',
        items=(
            ('FINISHED', 'Finished', 'Render or animation ready asset'),
            ('TEMPLATE', 'Template', 'Asset intended to help in creation of something else'),
        ),
        default='FINISHED',
        description='Production state of the asset, \n also template should be actually finished, \n'
                    'just the nature of it can be a template, like a thumbnailer scene, \n '
                    'finished mesh topology as start for modelling or similar',
    )

    engine_other: StringProperty(
        name="Engine",
        description="engine not specified by addon",
        default="",
    )

    engine1: EnumProperty(
        name='2nd Engine',
        items=engines,
        default='NONE',
        description='Output engine',
    )
    engine2: EnumProperty(
        name='3rd Engine',
        items=engines,
        default='NONE',
        description='Output engine',
    )
    engine3: EnumProperty(
        name='4th Engine',
        items=engines,
        default='NONE',
        description='Output engine',
    )

    thumbnail: StringProperty(
        name="Thumbnail",
        description="Thumbnail path - 512x512 .jpg\n"
                    "Rendered with cycles",
        subtype='FILE_PATH',
        default="",
        update=autothumb.update_upload_scene_preview)

    use_design_year: BoolProperty(name="Use Design Year",
                                  description="When this thing came into world for the first time\n"
                                              " e.g. for dinosaur, you set -240 million years ;) ",
                                  default=False)
    design_year: IntProperty(name="Design Year", description="when was this item designed", default=1960)
    # use_age : BoolProperty( name = "use item age", description = "use item age", default = False)
    condition: EnumProperty(
        items=conditions,
        default='UNSPECIFIED',
        description='age of the object',
    )

    adult: BoolProperty(name="Adult Content", description="adult content", default=False)

    work_hours: FloatProperty(name="Work Hours", description="How long did it take you to finish the asset?",
                              default=0.0, min=0.0, max=8760)

    modifiers: StringProperty(
        name="Modifiers Used",
        description="if you need specific modifiers, autofilled",
        default="",
    )

    materials: StringProperty(
        name="Material Names",
        description="names of materials in the file, autofilled",
        default="",
    )
    shaders: StringProperty(
        name="Shaders Used",
        description="shaders used in asset, autofilled",
        default="",
    )

    dimensions: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(0, 0, 0),
    )
    bbox_min: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(-.25, -.25, 0),
    )
    bbox_max: FloatVectorProperty(
        name="Dimensions",
        description="dimensions of the whole asset hierarchy",
        default=(.25, .25, .5),
    )

    texture_resolution_min: IntProperty(name="Texture Resolution Min",
                                        description="texture resolution min, autofilled", default=0)
    texture_resolution_max: IntProperty(name="Texture Resolution Max",
                                        description="texture resolution max, autofilled", default=0)

    pbr: BoolProperty(name="PBR Compatible", description="Is compatible with PBR standard", default=False)

    uv: BoolProperty(name="Has UV", description="has an UV set", default=False)
    # printable_3d : BoolProperty( name = "3d printable", description = "can be 3d printed", default = False)
    animated: BoolProperty(name="Animated", description="is animated", default=False)
    face_count: IntProperty(name="Face Count", description="face count, autofilled", default=0)
    face_count_render: IntProperty(name="Render Face Count", description="render face count, autofilled", default=0)

    object_count: IntProperty(name="Number of Objects", description="how many objects are in the asset, autofilled",
                              default=0)
    mesh_poly_type: EnumProperty(
        name='Dominant Poly Type',
        items=mesh_poly_types,
        default='OTHER',
        description='',
    )

    rig: BoolProperty(name="Rig", description="asset is rigged, autofilled", default=False)
    simulation: BoolProperty(name="Simulation", description="asset uses simulation, autofilled", default=False)

    # THUMBNAIL STATES
    is_generating_thumbnail: BoolProperty(name="Generating Thumbnail",
                                          description="True when background process is running", default=False,
                                          update=autothumb.update_upload_model_preview)

    has_autotags: BoolProperty(name="Has Autotagging Done", description="True when autotagging done", default=False)


class BlenderKitModelSearchProps(PropertyGroup, BlenderKitCommonSearchProps):
    search_keywords: StringProperty(
        name="Search",
        description="Search for these keywords",
        default="",
        update=search.search_update
    )
    search_style: EnumProperty(
        name="Style",
        items=search_model_styles,
        description="Keywords defining style (realistic, painted, polygonal, other)",
        default="ANY",
        update=search.search_update
    )
    search_style_other: StringProperty(
        name="Style",
        description="Search style - other",
        default="",
        update=search.search_update
    )
    search_engine: EnumProperty(
        items=engines,
        default='CYCLES',
        description='Output engine',
        update=search.search_update
    )
    search_engine_other: StringProperty(
        name="Engine",
        description="Engine not specified by addon",
        default="",
        update=search.search_update
    )

    # CONDITION
    search_condition: EnumProperty(
        items=conditions,
        default='UNSPECIFIED',
        description='Condition of the object',
        update=search.search_update
    )

    search_adult: BoolProperty(
        name="Adult Content",
        description="You're adult and agree with searching adult content",
        default=False,
        update=search.search_update
    )

    # DESIGN YEAR
    search_design_year: BoolProperty(name="Sesigned in Year",
                                     description="When the object was approximately designed. \n"
                                                 "Useful for search of historical or future objects",
                                     default=False,
                                     update=search.search_update,
                                     )

    search_design_year_min: IntProperty(name="Minimum Design Year",
                                        description="Minimum design year",
                                        default=1950, min=-100000000, max=1000000000,
                                        update=search.search_update,
                                        )

    search_design_year_max: IntProperty(name="Maximum Design Year",
                                        description="Maximum design year",
                                        default=2017,
                                        min=0,
                                        max=10000000,
                                        update=search.search_update,
                                        )

    # POLYCOUNT
    search_polycount: BoolProperty(name="Use Polycount",
                                   description="Limit polycount",
                                   default=False,
                                   update=search.search_update, )

    search_polycount_min: IntProperty(name="Min Polycount",
                                      description="Minimum poly count",
                                      default=0,
                                      min=0,
                                      max=100000000,
                                      update=search.search_update, )

    search_polycount_max: IntProperty(name="Max Polycount",
                                      description="Maximum poly count",
                                      default=100000000,
                                      min=0,
                                      max=100000000,
                                      update=search.search_update,
                                      )

    append_method: EnumProperty(
        name="Import Method",
        items=(
            ('LINK_COLLECTION', 'Link', 'Link Collection'),
            ('APPEND_OBJECTS', 'Append', 'Append as Objects'),
        ),
        description="Appended objects are editable in your scene. Linked assets are saved in original files, "
                    "aren't editable but also don't increase your file size",
        default="APPEND_OBJECTS"
    )
    append_link: EnumProperty(
        name="How to Attach",
        items=(
            ('LINK', 'Link', ''),
            ('APPEND', 'Append', ''),
        ),
        description="choose if the assets will be linked or appended",
        default="LINK"
    )
    import_as: EnumProperty(
        name="Import as",
        items=(
            ('GROUP', 'group', ''),
            ('INDIVIDUAL', 'objects', ''),

        ),
        description="choose if the assets will be linked or appended",
        default="GROUP"
    )
    randomize_rotation: BoolProperty(name='Randomize Rotation',
                                     description="randomize rotation at placement",
                                     default=False)
    randomize_rotation_amount: FloatProperty(name="Randomization Max Angle",
                                             description="maximum angle for random rotation",
                                             default=math.pi / 36,
                                             min=0,
                                             max=2 * math.pi,
                                             subtype='ANGLE')
    offset_rotation_amount: FloatProperty(name="Offset Rotation",
                                          description="offset rotation, hidden prop",
                                          default=0,
                                          min=0,
                                          max=360,
                                          subtype='ANGLE')
    offset_rotation_step: FloatProperty(name="Offset Rotation Step",
                                        description="offset rotation, hidden prop",
                                        default=math.pi / 2,
                                        min=0,
                                        max=180,
                                        subtype='ANGLE')

    perpendicular_snap: BoolProperty(name='Perpendicular snap',
                                     description="Limit snapping that is close to perpendicular angles to be perpendicular",
                                     default=True)

    perpendicular_snap_threshold: FloatProperty(name="Threshold",
                                                description="Limit perpendicular snap to be below these values",
                                                default=.25,
                                                min=0,
                                                max=.5,
                                                )


class BlenderKitHDRSearchProps(PropertyGroup, BlenderKitCommonSearchProps):
    search_keywords: StringProperty(
        name="Search",
        description="Search for these keywords",
        default="",
        update=search.search_update
    )

    true_hdr: BoolProperty(
        name='Real HDRs only',
        description='Search only for real HDRs, this means images that have a range higher than 0-1 in their pixels.',
        default=True,
        update=search.search_update
    )


class BlenderKitSceneSearchProps(PropertyGroup, BlenderKitCommonSearchProps):
    search_keywords: StringProperty(
        name="Search",
        description="Search for these keywords",
        default="",
        update=search.search_update
    )
    search_style: EnumProperty(
        name="Style",
        items=search_model_styles,
        description="Restrict search for style",
        default="ANY",
        update=search.search_update
    )
    search_style_other: StringProperty(
        name="Style",
        description="Search style - other",
        default="",
        update=search.search_update
    )
    search_engine: EnumProperty(
        items=engines,
        default='CYCLES',
        description='Output engine',
        update=search.search_update
    )
    search_engine_other: StringProperty(
        name="Engine",
        description="Engine not specified by addon",
        default="",
        update=search.search_update
    )
    append_link: EnumProperty(
        name="Append or link",
        items=(
            ('LINK', 'Link', ''),
            ('APPEND', 'Append', ''),
        ),
        description="choose if the scene will be linked or appended",
        default="APPEND"
    )
    switch_after_append: BoolProperty(
        name='Switch to scene after download',
        default=True
    )


def fix_subdir(self, context):
    '''Fixes project subdicrectory settings if people input invalid path.'''

    # pp = pathlib.PurePath(self.project_subdir)
    pp = self.project_subdir[:]
    pp = pp.replace('\\', '')
    pp = pp.replace('/', '')
    pp = pp.replace(':', '')
    pp = '//' + pp
    if self.project_subdir != pp:
        self.project_subdir = pp

        ui_panels.ui_message(title="Fixed to relative path",
                             message="This path should be always realative.\n" \
                                     " It's a directory BlenderKit creates where your .blend is \n " \
                                     "and uses it for storing assets.")


class BlenderKitAddonPreferences(AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__

    default_global_dict = paths.default_global_dict()

    enable_oauth = True

    api_key: StringProperty(
        name="BlenderKit API Key",
        description="Your blenderkit API Key. Get it from your page on the website",
        default="",
        subtype="PASSWORD",
        update=utils.save_prefs
    )

    api_key_refresh: StringProperty(
        name="BlenderKit refresh API Key",
        description="API key used to refresh the token regularly",
        default="",
        subtype="PASSWORD",
    )

    api_key_timeout: IntProperty(
        name='api key timeout',
        description='time where the api key will need to be refreshed',
        default=0,
    )

    api_key_life: IntProperty(
        name='api key life time',
        description='maximum lifetime of the api key, in seconds',
        default=0,
    )

    refresh_in_progress: BoolProperty(
        name="Api key refresh in progress",
        description="Api key is currently being refreshed. Don't refresh it again",
        default=False
    )

    login_attempt: BoolProperty(
        name="Login/Signup attempt",
        description="When this is on, BlenderKit is trying to connect and login",
        default=False
    )

    show_on_start: BoolProperty(
        name="Show assetbar when starting blender",
        description="Show assetbar when starting blender",
        default=False
    )

    tips_on_start: BoolProperty(
        name="Show tips when starting blender",
        description="Show tips when starting blender",
        default=False
    )

    search_in_header: BoolProperty(
        name="Show BlenderKit search in 3D view header",
        description="Show BlenderKit search in 3D view header",
        default=True
    )

    global_dir: StringProperty(
        name="Global Files Directory",
        description="Global storage for your assets, will use subdirectories for the contents",
        subtype='DIR_PATH',
        default=default_global_dict,
        update=utils.save_prefs
    )

    project_subdir: StringProperty(
        name="Project Assets Subdirectory",
        description="where data will be stored for individual projects",
        # subtype='DIR_PATH',
        default="//assets",
        update=fix_subdir
    )

    directory_behaviour: EnumProperty(
        name="Use Directories",
        items=(
            ('BOTH', 'Global and subdir',
             'store files both in global lib and subdirectory of current project. '
             'Warning - each file can be many times on your harddrive, but helps you keep your projects in one piece'),
            ('GLOBAL', 'Global',
             "store downloaded files only in global directory. \n "
             "This can bring problems when moving your projects, \n"
             "since assets won't be in subdirectory of current project"),
            ('LOCAL', 'Local',
             'store downloaded files only in local directory.\n'
             ' This can use more bandwidth when you reuse assets in different projects. ')

        ),
        description="Which directories will be used for storing downloaded data",
        default="BOTH",
    )
    thumbnail_use_gpu: BoolProperty(
        name="Use GPU for Thumbnails Rendering (For assets upload)",
        description="By default this is off so you can continue your work without any lag",
        default=False
    )

    panel_behaviour: EnumProperty(
        name="Panels Locations",
        items=(
            ('BOTH', 'Both Types',
             ''),
            ('UNIFIED', 'Unified 3D View Panel',
             ""),
            ('LOCAL', 'Relative to Data',
             '')

        ),
        description="Which directories will be used for storing downloaded data",
        default="UNIFIED",
    )

    max_assetbar_rows: IntProperty(name="Max Assetbar Rows",
                                   description="max rows of assetbar in the 3D view",
                                   default=1,
                                   min=1,
                                   max=20)

    thumb_size: IntProperty(name="Assetbar thumbnail Size", default=96, min=-1, max=256)

    asset_counter: IntProperty(name="Usage Counter",
                               description="Counts usages so it asks for registration only after reaching a limit",
                               default=0,
                               min=0,
                               max=20000)

    # this is now made obsolete by the new popup upon registration -ensures the user knows about the first search.
    # first_run: BoolProperty(
    #     name="First run",
    #     description="Detects if addon was already registered/run.",
    #     default=True,
    #     update=utils.save_prefs
    # )

    use_timers: BoolProperty(
        name="Use timers",
        description="Use timers for BlenderKit. Usefull for debugging since timers seem to be unstable",
        default=True,
        update=utils.save_prefs
    )

    # single_timer: BoolProperty(
    #     name="Use timers",
    #     description="Use timers for BlenderKit. Usefull for debugging since timers seem to be unstable",
    #     default=True,
    #     update=utils.save_prefs
    # )

    experimental_features: BoolProperty(
        name="Enable experimental features",
        description="Enable all experimental features of BlenderKit. Use at your own risk",
        default=False,
        update=utils.save_prefs
    )

    categories_fix: BoolProperty(
        name="Enable category fixing mode",
        description="Enable category fixing mode",
        default=False,
        update=utils.save_prefs
    )

    # allow_proximity : BoolProperty(
    #     name="allow proximity data reports",
    #     description="This sends anonymized proximity data \n \
    #             and allows us to make relations between database objects \n \
    #              without user interaction",
    #     default=False
    # )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "show_on_start")

        if self.api_key.strip() == '':
            if self.enable_oauth:
                ui_panels.draw_login_buttons(layout)
            else:
                op = layout.operator("wm.url_open", text="Register online and get your API Key",
                                     icon='QUESTION')
                op.url = paths.BLENDERKIT_SIGNUP_URL
        else:
            if self.enable_oauth:
                layout.operator("wm.blenderkit_logout", text="Logout",
                                icon='URL')

        # if not self.enable_oauth:
        layout.prop(self, "api_key", text='Your API Key')
        # layout.label(text='After you paste API Key, categories are downloaded, so blender will freeze for a few seconds.')
        layout.prop(self, "global_dir")
        layout.prop(self, "project_subdir")
        # layout.prop(self, "temp_dir")
        layout.prop(self, "directory_behaviour")
        # layout.prop(self, "allow_proximity")
        # layout.prop(self, "panel_behaviour")
        layout.prop(self, "thumb_size")
        layout.prop(self, "max_assetbar_rows")
        layout.prop(self, "tips_on_start")
        layout.prop(self, "search_in_header")
        layout.prop(self, "thumbnail_use_gpu")

        if bpy.context.preferences.view.show_developer_ui:
            layout.prop(self, "use_timers")
            layout.prop(self, "experimental_features")
            layout.prop(self, "categories_fix")


# # @bpy.app.handlers.persistent
# def blenderkit_timer():
#
#
# if not user_preferences.use_timers:
#     search.search_timer()
#     download.download_timer()
#     tasks_queue.queue_worker()
#     bg_blender.bg_update()
# registration
classes = (

    BlenderKitAddonPreferences,
    BlenderKitUIProps,

    BlenderKitModelSearchProps,
    BlenderKitModelUploadProps,

    BlenderKitSceneSearchProps,
    BlenderKitSceneUploadProps,

    BlenderKitHDRSearchProps,
    BlenderKitHDRUploadProps,

    BlenderKitMaterialUploadProps,
    BlenderKitMaterialSearchProps,

    BlenderKitTextureUploadProps,

    BlenderKitBrushSearchProps,
    BlenderKitBrushUploadProps,

    BlenderKitRatingProps,
)



def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.blenderkitUI = PointerProperty(
        type=BlenderKitUIProps)

    # MODELS
    bpy.types.WindowManager.blenderkit_models = PointerProperty(
        type=BlenderKitModelSearchProps)
    bpy.types.Object.blenderkit = PointerProperty(  # for uploads, not now...
        type=BlenderKitModelUploadProps)
    bpy.types.Object.bkit_ratings = PointerProperty(  # for uploads, not now...
        type=BlenderKitRatingProps)

    # SCENES
    bpy.types.WindowManager.blenderkit_scene = PointerProperty(
        type=BlenderKitSceneSearchProps)
    bpy.types.Scene.blenderkit = PointerProperty(  # for uploads, not now...
        type=BlenderKitSceneUploadProps)
    bpy.types.Scene.bkit_ratings = PointerProperty(  # for uploads, not now...
        type=BlenderKitRatingProps)

    # HDRs
    bpy.types.WindowManager.blenderkit_HDR = PointerProperty(
        type=BlenderKitHDRSearchProps)
    bpy.types.Image.blenderkit = PointerProperty(  # for uploads, not now...
        type=BlenderKitHDRUploadProps)
    bpy.types.Image.bkit_ratings = PointerProperty(  # for uploads, not now...
        type=BlenderKitRatingProps)

    # MATERIALS
    bpy.types.WindowManager.blenderkit_mat = PointerProperty(
        type=BlenderKitMaterialSearchProps)
    bpy.types.Material.blenderkit = PointerProperty(  # for uploads, not now...
        type=BlenderKitMaterialUploadProps)
    bpy.types.Material.bkit_ratings = PointerProperty(  # for uploads, not now...
        type=BlenderKitRatingProps)

    # BRUSHES
    bpy.types.WindowManager.blenderkit_brush = PointerProperty(
        type=BlenderKitBrushSearchProps)
    bpy.types.Brush.blenderkit = PointerProperty(  # for uploads, not now...
        type=BlenderKitBrushUploadProps)
    bpy.types.Brush.bkit_ratings = PointerProperty(  # for uploads, not now...
        type=BlenderKitRatingProps)

    search.register_search()
    asset_inspector.register_asset_inspector()
    download.register_download()
    upload.register_upload()
    ratings.register_ratings()
    autothumb.register_thumbnailer()
    ui.register_ui()
    icons.register_icons()
    ui_panels.register_ui_panels()
    bg_blender.register()
    utils.load_prefs()
    overrides.register_overrides()
    bkit_oauth.register()
    tasks_queue.register()
    asset_bar_op.register()

    user_preferences = bpy.context.preferences.addons['blenderkit'].preferences
    if user_preferences.use_timers:
        bpy.app.timers.register(check_timers_timer, persistent=True)

    bpy.app.handlers.load_post.append(scene_load)
    # detect if the user just enabled the addon in preferences, thus enable to run
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type == 'PREFERENCES':
                tasks_queue.add_task((bpy.ops.wm.blenderkit_welcome, ('INVOKE_DEFAULT',)), fake_context=True,
                                     fake_context_area='PREFERENCES')
                #save preferences after manually enabling the addon
                tasks_queue.add_task((bpy.ops.wm.save_userpref, ()), fake_context=False,)


def unregister():
    if bpy.app.timers.is_registered(check_timers_timer):
        bpy.app.timers.unregister(check_timers_timer)
    ui_panels.unregister_ui_panels()
    ui.unregister_ui()

    icons.unregister_icons()
    search.unregister_search()
    asset_inspector.unregister_asset_inspector()
    download.unregister_download()
    upload.unregister_upload()
    ratings.unregister_ratings()
    autothumb.unregister_thumbnailer()
    bg_blender.unregister()
    overrides.unregister_overrides()
    bkit_oauth.unregister()
    tasks_queue.unregister()
    asset_bar_op.unregister()

    del bpy.types.WindowManager.blenderkit_models
    del bpy.types.WindowManager.blenderkit_scene
    del bpy.types.WindowManager.blenderkit_HDR
    del bpy.types.WindowManager.blenderkit_brush
    del bpy.types.WindowManager.blenderkit_mat

    del bpy.types.Scene.blenderkit
    del bpy.types.Object.blenderkit
    del bpy.types.Image.blenderkit
    del bpy.types.Material.blenderkit
    del bpy.types.Brush.blenderkit

    for cls in classes:
        bpy.utils.unregister_class(cls)

    bpy.app.handlers.load_post.remove(scene_load)
