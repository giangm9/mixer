import bpy
import logging
import time

from mixer.blender_data import blenddata

logger = logging.Logger(__name__, logging.INFO)
default_test = "test_module.TestCase.test_name"


class DebugDataProperties(bpy.types.PropertyGroup):
    profile_cumulative: bpy.props.BoolProperty(name="ProfileCumulative", default=False)
    profile_callers: bpy.props.BoolProperty(name="ProfileCallers", default=False)
    test_names: bpy.props.StringProperty(name="TestNames", default=default_test)


def timeit(func):
    def wrapper(*arg, **kw):
        """source: http://www.daniweb.com/code/snippet368.html"""
        t1 = time.time()
        res = func(*arg, **kw)
        t2 = time.time()
        return (t2 - t1), res, func.__name__

    return wrapper


class BuildProxyOperator(bpy.types.Operator):
    """Build proxy from current file"""

    bl_idname = "mixer.build_proxy"
    bl_label = "Mixer build proxy"
    bl_options = {"REGISTER"}

    def execute(self, context):
        # Cannot import at module level, since it requires access to bpy.data which is not
        # accessible during module load
        from mixer.blender_data.proxy import BpyBlendProxy
        from mixer.blender_data.filter import test_context
        import cProfile
        import io
        import pstats
        from pstats import SortKey

        profile_cumulative = get_props().profile_cumulative
        profile_callers = get_props().profile_callers
        profile = profile_callers or profile_cumulative
        proxy = BpyBlendProxy()
        if profile:
            pr = cProfile.Profile()
            pr.enable()
        t1 = time.time()
        proxy.load(test_context)
        t2 = time.time()
        if profile:
            pr.disable()
            s = io.StringIO()
            sortby = SortKey.CUMULATIVE
            ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            if profile_cumulative:
                ps.print_stats()
            if profile_callers:
                ps.print_callers()
            print(s.getvalue())

        logger.warning(f"Elapse: {t2 - t1} s.")
        non_empty = proxy.get_non_empty_collections()
        logger.info(f"Number of non empty collections in proxy: {len(non_empty)}")

        # Put breakpoint here and examinate non_empty dictionnary
        return {"FINISHED"}


class DebugDataTestOperator(bpy.types.Operator):
    """Execute blender_data tests for debugging"""

    bl_idname = "mixer.data_test"
    bl_label = "Mixer test data"
    bl_options = {"REGISTER"}

    def execute(self, context):
        # Cannot import at module level, since it requires access to bpy.data which is not
        # accessible during module load
        from mixer.blender_data.tests.utils import run_tests

        names = get_props().test_names
        if names:
            base = "mixer.blender_data.tests."
            test_names = [base + name for name in names.split()]
        else:
            test_names = None

        run_tests(test_names)

        return {"FINISHED"}


class DebugDataPanel(bpy.types.Panel):
    """blender_data debug Panel"""

    bl_label = "Data"
    bl_idname = "DATA_PT_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Mixer"

    def draw(self, context):
        layout = self.layout

        row = layout.column()
        row.operator(BuildProxyOperator.bl_idname, text="Build Proxy")
        row.prop(get_props(), "profile_cumulative", text="Profile Cumulative")
        row.prop(get_props(), "profile_callers", text="Profile callers")
        row.operator(DebugDataTestOperator.bl_idname, text="Test")
        row = layout.row()
        row.prop(get_props(), "test_names", text="Test")


classes = (
    BuildProxyOperator,
    DebugDataTestOperator,
    DebugDataPanel,
    DebugDataProperties,
)


def get_props() -> DebugDataProperties:
    return bpy.context.window_manager.debug_data_props


def register():
    for class_ in classes:
        bpy.utils.register_class(class_)
    bpy.types.WindowManager.debug_data_props = bpy.props.PointerProperty(type=DebugDataProperties)
    blenddata.register()


def unregister():
    for class_ in classes:
        bpy.utils.unregister_class(class_)
    blenddata.unregister()
