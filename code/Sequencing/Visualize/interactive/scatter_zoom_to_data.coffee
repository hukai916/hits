models = cb_obj.document._all_models_by_name._dict

scatter_data = models['scatter_source'].data
x_range = models['x_range']
y_range = models['y_range']

xs = scatter_data.x
ys = scatter_data.y

clean_xs = (x for x, i in xs when x isnt 'NaN' and ys[i] isnt 'NaN')
x_max = Math.max(clean_xs...)
x_min = Math.min(clean_xs...)
x_buffer = (x_max - x_min) * 0.05
x_range.start = x_min - x_buffer
x_range.end = x_max + x_buffer

clean_ys = (y for y, i in ys when y isnt 'NaN' and xs[i] isnt 'NaN')
y_max = Math.max(clean_ys...)
y_min = Math.min(clean_ys...)
y_buffer = (y_max - y_min) * 0.05
y_range.start = y_min - y_buffer
y_range.end = y_max + y_buffer
