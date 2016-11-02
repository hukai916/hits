import numpy as np
import bokeh.io
import bokeh.plotting
import pandas as pd
import PIL.ImageColor
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

def scatter(df, hover_keys=None, table_keys=None, size=900, log_scale=False):
    ''' Makes an interactive scatter plot using bokeh.

    Args:
            df: A pandas DataFrame with columns containing numerical data to plot.
                If 'color' is a column, it will be used to color the points. 
                Index values will be used as labels for points. Any text columns
                will be searchable through the 'Search:' field.
            hover_keys: Names of columns in df to display in the tooltip that appears
                when you hover over a point.
            table_keys: Names of columns in df to display in the table below the plot
                that is populated with the selected points from the figure.
    '''

    if hover_keys is None:
        hover_keys = []

    if table_keys is None:
        table_keys = []

    # Set up the actual scatter plot.
    
    tools = [
        'reset',
        'pan',
        'box_zoom',
        'box_select',
        'tap',
        'wheel_zoom',
        'save',
    ]
    
    fig_kwargs = {
        'plot_width': size,
        'plot_height': size,
        'tools': tools,
        'lod_threshold': 10000,
    }
    if log_scale:
        fig_kwargs['y_axis_type'] = 'log'
        fig_kwargs['x_axis_type'] = 'log'
    
    fig = bokeh.plotting.figure(**fig_kwargs)

    fig.grid.visible = False
    fig.grid.name = 'grid'
    
    lasso = bokeh.models.LassoSelectTool(select_every_mousemove=False)
    fig.add_tools(lasso)

    numerical_cols = [n for n in df.columns if df[n].dtype in [float, int]]
    nonnumerical_cols = [n for n in df.columns | [df.index.name] if n not in numerical_cols]

    x_name, y_name = numerical_cols[:2]
    
    fig.xaxis.axis_label = x_name
    fig.yaxis.axis_label = y_name
    for axis in (fig.xaxis, fig.yaxis):
        axis.axis_label_text_font_size = '20pt'
        axis.axis_label_text_font_style = 'normal'

    scatter_source = bokeh.models.ColumnDataSource(data=df)

    scatter_source.data['x'] = scatter_source.data[x_name]
    scatter_source.data['y'] = scatter_source.data[y_name]

    if 'color' not in df:
        scatter_source.data['color'] = ['rgba(0, 0, 0, 0.5)' for _ in scatter_source.data['x']]

    if df.index.name is None:
        df.index.name = 'index'
    
    scatter = fig.scatter('x',
                          'y',
                          source=scatter_source,
                          size=6,
                          fill_color='color',
                          line_color=None,
                         )
    
    overall_max = df.max(numeric_only=True).max()
    overall_min = df.min(numeric_only=True).min()
    
    extent = overall_max - overall_min
    overhang = extent * 0.05
    max_overhang = extent * 0.5
    
    if log_scale:
        initial = (overall_min * 0.1, overall_max * 10)
        bounds = (overall_min * 0.001, overall_max * 1000)
    else:
        initial = (overall_min - overhang, overall_max + overhang)
        bounds = (overall_min - max_overhang, overall_max + max_overhang)

    fig.line(x=bounds, y=bounds, color='black', alpha=0.4, name='diagonal')
    if log_scale:
        upper_ys = np.array(bounds) * 10
        lower_ys = np.array(bounds) * 0.1
    else:
        upper_ys = np.array(bounds) + 1
        lower_ys = np.array(bounds) - 1

    fig.line(x=bounds, y=upper_ys, color='black', alpha=0.2, line_dash=[5, 5], name='diagonal')
    fig.line(x=bounds, y=lower_ys, color='black', alpha=0.2, line_dash=[5, 5], name='diagonal')
    
    fig.y_range = bokeh.models.Range1d(*initial, bounds=bounds)
    fig.x_range = bokeh.models.Range1d(*initial, bounds=bounds)

    if 'color' not in df:
        scatter.selection_glyph = bokeh.models.Circle(fill_color="orange",
                                                      line_color=None,
                                                     )

    scatter.nonselection_glyph = bokeh.models.Circle(fill_color="black",
                                                     line_color=None,
                                                     fill_alpha=0.1,
                                                    )

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
    filtered_source = bokeh.models.ColumnDataSource(data=filtered_data)
    
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

    menu_args = dict(scatter_source=scatter.data_source,
                     label_source=labels.source,
                     x_menu=x_menu,
                     y_menu=y_menu,
                     xaxis=fig.xaxis[0],
                     yaxis=fig.yaxis[0],
                    )
    menu_callback = external_coffeescript('scatter_menu', args=menu_args)
    x_menu.callback = menu_callback
    y_menu.callback = menu_callback
    
    # Set up callback to filter the table when selection changes.

    selection_args = dict(source=scatter_source, table=table, labels=labels)
    scatter_source.callback = external_coffeescript('scatter_selection', args=selection_args)
    
    # Button to toggle labels.
    
    button = bokeh.models.widgets.Toggle(label='label selected points',
                                         width=50,
                                         active=True,
                                        )
    button.callback = bokeh.models.CustomJS(args={'labels': labels},
                                            code='labels.text_alpha = 1 - labels.text_alpha;',
                                           )

    grid_options = bokeh.models.widgets.RadioGroup(labels=['grid', 'diagonal'], active=1)
    grid_options.callback = external_coffeescript('scatter_grid')

    text_input = bokeh.models.widgets.TextInput(title='Search:')
    text_input.callback = external_coffeescript('scatter_search',
                                                format_args=dict(columns=nonnumerical_cols),
                                                args=dict(scatter_source=scatter.data_source,
                                                          labels=labels,
                                                          table=table,
                                                         ),
                                               )

    grid = [
        [bokeh.layouts.widgetbox([x_menu, y_menu])],
        [fig, bokeh.layouts.widgetbox([button, grid_options, text_input])],
        [table],
    ]
    layout = bokeh.layouts.layout(grid)
    bokeh.io.show(layout)

def hex_to_CSS(hex_string, alpha=1.):
    ''' Converts an RGB hex value and option alpha value to a CSS-format RGBA string. '''
    rgb = PIL.ImageColor.getrgb(hex_string)
    CSS = 'rgba({1}, {2}, {3}, {0})'.format(alpha, *rgb)
    return CSS

def example():
    fn = os.path.join(os.path.dirname(__file__), 'example_df.txt') 
    df = pd.read_csv(fn, index_col='alias')
    scatter(df, hover_keys=['short_description'], table_keys=['description'])

def metacodon(xs, ys, colors, groupings):
    sources = {}
    data = defaultdict(dict)
    for key in ['plotted', 'codon', 'nucleotide']:
        if key == 'plotted':
            resolution = 'codon'
        else:
            resolution = key
        
        sources[key] = {}
        for checkbox_name in sorted(ys[resolution]):
            source = bokeh.models.ColumnDataSource(ys[resolution][checkbox_name])
            source.data['x'] = xs[resolution]
            source.data['y'] = source.data[sorted(ys[resolution][checkbox_name])[0]]
            source.data['name'] = [checkbox_name] * len(xs[resolution])
            source.name = 'source_{0}_{1}'.format(checkbox_name, key)
            sources[key][checkbox_name] = source
   
    tools = ['pan', 'tap', 'box_zoom', 'wheel_zoom', 'save', 'reset']
    fig = bokeh.plotting.figure(plot_width=1200, plot_height=800, tools=tools)

    fig.y_range = bokeh.models.Range1d(0, 5, bounds=(-1, 50))
    fig.x_range = bokeh.models.Range1d(-25, 25, bounds=(-100, 100))

    legend_items = []
    lines = []
    for checkbox_name, source in sources['plotted'].items():
        line = fig.line(x='x',
                        y='y',
                        color='black',
                        source=source,
                        line_width=1,
                        line_alpha=0.6,
                        line_join='round',
                        hover_alpha=1.0,
                        hover_color=colors[checkbox_name],
                        legend=checkbox_name,
                       )
        line.hover_glyph.line_width = 4
        line.name = 'line_{0}'.format(checkbox_name)
        lines.append(line)
        
        circle = fig.circle(x='x',
                            y='y',
                            color='black',
                            source=source,
                            size=4,
                            fill_alpha=0.9,
                            line_alpha=0.9,
                            visible=False,
                            hover_alpha=1.0,
                            hover_color=colors[checkbox_name],
                           )
        circle.hover_glyph.visible = True
        circle.name = 'circle_{0}'.format(checkbox_name)
    
        legend_items.append((checkbox_name, [line]))
        
    fig.legend.name = 'legend'
    fig.legend.items = []
        
    invisible_legend = bokeh.models.Legend(items=legend_items, name='invisible_legend')
    
    source_callback = external_coffeescript('metacodon_selection',
                                            args=dict(invisible_legend=invisible_legend),
                                           )
    for source in sources['plotted'].values():
        source.callback = source_callback

    hover = bokeh.models.HoverTool(line_policy='interp',
                                   renderers=lines,
                                  )
    hover.tooltips = [('name', '@name')]
    fig.add_tools(hover)

    zero = bokeh.models.annotations.Span(location=0,
                                         dimension='height',
                                         line_color='black',
                                         line_alpha=0.8,
                                         line_dash='dashed',
                                        )
    fig.renderers.append(zero)

    options = sorted(ys['codon'].values()[0].keys())
    menu = bokeh.models.widgets.Select(options=options, value=options[0])
    menu.callback = external_coffeescript('metacodon_menu')

    sub_group_callback = external_coffeescript('metacodon_sub_group',
                                               format_args=dict(colors_dict=str(colors)),
                                               args=dict(invisible_legend=invisible_legend),
                                              )

    top_group_callback = external_coffeescript('metacodon_top_group',
                                               args=dict(invisible_legend=invisible_legend),
                                              )

    top_groups = []
    sub_groups = []
    width = 75 + max(len(l) for top_name in groupings for l in groupings[top_name]) * 5
    for top_name, sub_names in sorted(groupings.items()):
        top = bokeh.models.widgets.CheckboxGroup(labels=[top_name],
                                                 active=[],
                                                 width=width,
                                                 name='top_{0}'.format(top_name),
                                                 callback=top_group_callback,
                                                )
        top_groups.append(top)
        sub = bokeh.models.widgets.CheckboxGroup(labels=sub_names,
                                                 active=[],
                                                 width=width,
                                                 callback=sub_group_callback,
                                                 name='sub_{0}'.format(top_name),
                                                )
        sub_groups.append(sub)

    resolution = bokeh.models.widgets.RadioGroup(labels=['codon resolution', 'nucleotide resolution'], active=0)
    injection_sources = sources['nucleotide'].values() + sources['codon'].values()
    injection = {'ensure_no_collision_{0}'.format(i): v for i, v in enumerate(injection_sources)}
    resolution.callback = external_coffeescript('metacodon_button',
                                                args=dict(fig=fig, **injection),
                                               )

    clear_selection = bokeh.models.widgets.Button(label='Clear selection')
    clear_selection.callback = external_coffeescript('metacodon_clear_selection',
                                                     args=dict(invisible_legend=invisible_legend),
                                                    )

    grid = [
        top_groups,
        sub_groups,
        [fig, bokeh.layouts.widgetbox([menu, resolution, clear_selection])],
    ]

    bokeh.io.show(bokeh.layouts.layout(grid))
