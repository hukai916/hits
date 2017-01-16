import numpy as np
import bokeh.io
import bokeh.plotting
#import bokeh.resources
import pandas as pd
import matplotlib.colors
import os.path
import glob
from collections import defaultdict

bokeh.io.output_notebook()

# For easier editing, coffeescript callbacks are kept in separate files
# in the same directory as this one. Load their contents into a dictionary.

coffee_fns = glob.glob(os.path.join(os.path.dirname(__file__), '*.coffee'))
callbacks = {}
for fn in coffee_fns:
    head, tail = os.path.split(fn)
    root, ext = os.path.splitext(tail)
    with open(fn) as fh:
        callbacks[root] = fh.read()

def external_coffeescript(key, args=None, format_args=None):
    if args is None:
        args = {}
    if format_args is None:
        format_args = {}

    code = callbacks[key].format(**format_args)
    callback = bokeh.models.CustomJS.from_coffeescript(code=code, args=args)
    return callback

colors_list = [ # from http://godsnotwheregodsnot.blogspot.ru/2012/09/color-distribution-methodology.html
    "#000000", "#FFFF00", "#1CE6FF", "#FF34FF", "#FF4A46", "#008941", "#006FA6", "#A30059",
    "#FFDBE5", "#7A4900", "#0000A6", "#63FFAC", "#B79762", "#004D43", "#8FB0FF", "#997D87",
    "#5A0007", "#809693", "#FEFFE6", "#1B4400", "#4FC601", "#3B5DFF", "#4A3B53", "#FF2F80",
    "#61615A", "#BA0900", "#6B7900", "#00C2A0", "#FFAA92", "#FF90C9", "#B903AA", "#D16100",
    "#DDEFFF", "#000035", "#7B4F4B", "#A1C299", "#300018", "#0AA6D8", "#013349", "#00846F",
    "#372101", "#FFB500", "#C2FFED", "#A079BF", "#CC0744", "#C0B9B2", "#C2FF99", "#001E09",
    "#00489C", "#6F0062", "#0CBD66", "#EEC3FF", "#456D75", "#B77B68", "#7A87A1", "#788D66",
    "#885578", "#FAD09F", "#FF8A9A", "#D157A0", "#BEC459", "#456648", "#0086ED", "#886F4C",
    "#34362D", "#B4A8BD", "#00A6AA", "#452C2C", "#636375", "#A3C8C9", "#FF913F", "#938A81",
    "#575329", "#00FECF", "#B05B6F", "#8CD0FF", "#3B9700", "#04F757", "#C8A1A1", "#1E6E00",
    "#7900D7", "#A77500", "#6367A9", "#A05837", "#6B002C", "#772600", "#D790FF", "#9B9700",
    "#549E79", "#FFF69F", "#201625", "#72418F", "#BC23FF", "#99ADC0", "#3A2465", "#922329",
    "#5B4534", "#FDE8DC", "#404E55", "#0089A3", "#CB7E98", "#A4E804", "#324E72", "#6A3A4C",
]

def scatter(df, hover_keys=None, table_keys=None, size=900, log_scale=False, volcano=False):
    ''' Makes an interactive scatter plot using bokeh.

    Args:
            df: A pandas DataFrame with columns containing numerical data to plot.
                If 'color' is a column, it will be used to color the points. 
                Index values will be used as labels for points.
                Any text columns will be searchable through the 'Search:' field.
                Any boolean columns will be used to define subset of points for
                selection from a dropdown menu.
            hover_keys: Names of columns in df to display in the tooltip that appears
                when you hover over a point.
            table_keys: Names of columns in df to display in the table below the plot
                that is populated with the selected points from the figure.
            size: Size of the plot in pixels.
    '''

    if hover_keys is None:
        hover_keys = []

    if table_keys is None:
        table_keys = []

    # Set up the actual scatter plot.
    
    tools = [
        'reset',
        'undo',
        'pan',
        'box_zoom',
        'box_select',
        'tap',
        'wheel_zoom',
        'save',
    ]
    
    fig_kwargs = dict(
        plot_width=size,
        plot_height=size,
        tools=tools,
        lod_threshold=10000,
    )

    if log_scale:
        if log_scale is True:
            log_scale = 10
        fig_kwargs['y_axis_type'] = 'log'
        fig_kwargs['x_axis_type'] = 'log'
    
    fig = bokeh.plotting.figure(**fig_kwargs)

    if log_scale:
        for axis in [fig.xaxis, fig.yaxis]:
            axis[0].ticker.base = log_scale
            axis[0].formatter.ticker = axis[0].ticker

    fig.grid.visible = volcano # i.e. normally False
    fig.grid.name = 'grid'
    
    lasso = bokeh.models.LassoSelectTool(select_every_mousemove=False)
    fig.add_tools(lasso)

    numerical_cols = [n for n in df.columns if df[n].dtype in [float, int]]

    object_cols = [n for n in df.columns if df[n].dtype is np.dtype('O')]
    if df.index.dtype is np.dtype('O'):
        object_cols.append(df.index.name)

    bool_cols = [n for n in df.columns if df[n].dtype is np.dtype('bool')]

    x_name, y_name = numerical_cols[:2]
    
    fig.xaxis.axis_label = x_name
    fig.yaxis.axis_label = y_name
    for axis in (fig.xaxis, fig.yaxis):
        axis.axis_label_text_font_size = '20pt'
        axis.axis_label_text_font_style = 'normal'

    scatter_source = bokeh.models.ColumnDataSource(data=df, name='scatter_source')

    scatter_source.data['x'] = scatter_source.data[x_name]
    scatter_source.data['y'] = scatter_source.data[y_name]

    scatter_source.data['no_color'] = ['rgba(0, 0, 0, 0.5)' for _ in scatter_source.data['x']]
    if 'color' not in scatter_source.data:
        scatter_source.data['color'] = scatter_source.data['no_color']

    if df.index.name is None:
        df.index.name = 'index'
    
    scatter = fig.scatter('x',
                          'y',
                          source=scatter_source,
                          size=6,
                          fill_color='color',
                          line_color=None,
                          nonselection_color='color',
                          nonselection_alpha=0.1,
                          selection_color='color',
                          selection_alpha=0.9,
                          name='scatter',
                         )
    
    if log_scale:
        nonzero = df[df > 0]

        overall_max = nonzero.max(numeric_only=True).max()
        overall_min = nonzero.min(numeric_only=True).min()

        initial = (overall_min * 0.1, overall_max * 10)
        bounds = (overall_min * 0.001, overall_max * 1000)
    else:
        overall_max = df.max(numeric_only=True).max()
        overall_min = df.min(numeric_only=True).min()

        extent = overall_max - overall_min
        overhang = extent * 0.05
        max_overhang = extent * 0.5

        initial = (overall_min - overhang, overall_max + overhang)
        bounds = (overall_min - max_overhang, overall_max + max_overhang)

    diagonals_visible = not volcano # i.e. normally True

    fig.line(x=bounds, y=bounds,
             color='black',
             nonselection_color='black',
             alpha=0.4,
             nonselection_alpha=0.4,
             name='diagonal',
             visible=diagonals_visible,
            )

    if log_scale:
        upper_ys = np.array(bounds) * 10
        lower_ys = np.array(bounds) * 0.1
    else:
        upper_ys = np.array(bounds) + 1
        lower_ys = np.array(bounds) - 1

    line_kwargs = dict(
        color='black',
        nonselection_color='black',
        alpha=0.4,
        nonselection_alpha=0.4,
        line_dash=[5, 5],
        name='diagonal',
        visible=diagonals_visible,
    ) 
    fig.line(x=bounds, y=upper_ys, **line_kwargs)
    fig.line(x=bounds, y=lower_ys, **line_kwargs)
    
    if volcano:
        fig.y_range = bokeh.models.Range1d(-0.1, 8)
        fig.x_range = bokeh.models.Range1d(-1, 1)
    else:
        fig.y_range = bokeh.models.Range1d(*initial, bounds=bounds)
        fig.x_range = bokeh.models.Range1d(*initial, bounds=bounds)

    fig.x_range.name = 'x_range'
    fig.y_range.name = 'y_range'

    scatter.selection_glyph.fill_color = "orange"
    scatter.selection_glyph.line_color = None
    scatter.nonselection_glyph.line_color = None

    # Configure tooltips that pop up when hovering over a point.
    
    hover = bokeh.models.HoverTool()
    hover.tooltips = [
        (df.index.name, '@{0}'.format(df.index.name)),
    ]
    for key in hover_keys:
        hover.tooltips.append((key, '@{0}'.format(key)))
    fig.add_tools(hover)

    # Set up the table.

    table_col_names = [df.index.name] + table_keys
    columns = []
    for col_name in table_col_names:
        if col_name == df.index.name:
            formatter = None
            width = 80
        elif col_name in numerical_cols:
            formatter = bokeh.models.widgets.NumberFormatter(format='0.00')
            width = 50
        else:
            formatter = None
            width = 500

        column = bokeh.models.widgets.TableColumn(field=col_name,
                                                  title=col_name,
                                                  formatter=formatter,
                                                  width=width,
                                                 )
        columns.append(column)

    filtered_data = {k: [] for k in list(df.columns) + [df.index.name, 'x', 'y']}
    filtered_source = bokeh.models.ColumnDataSource(data=filtered_data, name='labels_source')
    
    labels = bokeh.models.LabelSet(x='x',
                                   y='y',
                                   text=df.index.name,
                                   level='glyph',
                                   x_offset=0,
                                   y_offset=2,
                                   source=filtered_source,
                                   text_font_size='8pt',
                                  )
    fig.add_layout(labels)
    
    table = bokeh.models.widgets.DataTable(source=filtered_source,
                                           columns=columns,
                                           width=size,
                                           height=1000,
                                           sortable=False,
                                           name='table',
                                          )
    
    # Set up menus to select columns from df to put on x- and y-axis.

    x_menu = bokeh.models.widgets.Select(title='X',
                                         options=numerical_cols,
                                         value=x_name,
                                        )
    y_menu = bokeh.models.widgets.Select(title='Y',
                                         options=numerical_cols,
                                         value=y_name,
                                        )

    menu_args = dict(x_menu=x_menu,
                     y_menu=y_menu,
                     xaxis=fig.xaxis[0],
                     yaxis=fig.yaxis[0],
                    )
    menu_callback = external_coffeescript('scatter_menu', args=menu_args)
    x_menu.callback = menu_callback
    y_menu.callback = menu_callback
    
    # Set up callback to filter the table when selection changes.
    scatter_source.callback = external_coffeescript('scatter_selection')
    
    # Button to toggle labels.
    button = bokeh.models.widgets.Toggle(label='label selected points',
                                         width=50,
                                         active=True,
                                        )
    button.callback = bokeh.models.CustomJS(args={'labels': labels},
                                            code='labels.text_alpha = 1 - labels.text_alpha;',
                                           )
    
    # Button to zoom to current data limits.
    zoom_to_data_button = bokeh.models.widgets.Button(label='zoom to data limits',
                                                      width=50,
                                                     )
    zoom_to_data_button.callback = external_coffeescript('scatter_zoom_to_data')

    grid_options = bokeh.models.widgets.RadioGroup(labels=['grid', 'diagonal'], active=1 if not volcano else 0)
    grid_options.callback = external_coffeescript('scatter_grid')

    text_input = bokeh.models.widgets.TextInput(title='Search:')
    text_input.callback = external_coffeescript('scatter_search',
                                                format_args=dict(columns=object_cols),
                                               )
    
    # Menu to select a subset of points from a columns of bools.
    subset_options = [''] + bool_cols
    subset_menu = bokeh.models.widgets.Select(title='Select subset:',
                                             options=subset_options,
                                             value='',
                                            )
    subset_menu.callback = external_coffeescript('scatter_subset_menu')

    # Button to dump table to file.
    save_button = bokeh.models.widgets.Button(label='Save table to file',
                                              width=50,
                                             )
    save_button.callback = external_coffeescript('scatter_save_button',
                                                 format_args=dict(columns=table_col_names),
                                                )

    grid = [
        [bokeh.layouts.widgetbox([x_menu, y_menu])],
        [fig, bokeh.layouts.widgetbox([button, zoom_to_data_button, grid_options, text_input, subset_menu, save_button])],
        [table],
    ]
    layout = bokeh.layouts.layout(grid)
    bokeh.io.show(layout)

def hex_to_CSS(hex_string, alpha=1.):
    ''' Converts an RGB hex value and option alpha value to a CSS-format RGBA string. '''
    rgb = matplotlib.colors.colorConverter.to_rgb(hex_string)
    CSS = 'rgba({1}, {2}, {3}, {0})'.format(alpha, *rgb)
    return CSS

def example():
    fn = os.path.join(os.path.dirname(__file__), 'example_df.txt') 
    df = pd.read_csv(fn, index_col='alias')
    scatter(df, hover_keys=['short_description'], table_keys=['description'])
