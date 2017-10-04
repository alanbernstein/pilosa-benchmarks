# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render

# Create your views here.
from core.models import Benchmark, Run
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.offline as opy
from collections import defaultdict
from django.views.generic.base import TemplateView


MICROSEC_TO_SEC = 0.000001

color_cycle = {
    'pilosa-blue': '#3C5F8D',
    # 'pilosa-light-blue': '#CFEAEC',
    'pilosa-green': '#1DB598',
    'pilosa-red': '#FF2B2B',
    'pilosa-dark-blue': '#102445',
    'orange': '#FFA500',
    'magenta': '#FF00FF',
    'lime': '#00FF00',
    'cyan': '#00FFFF',
    'dark-yellow': '#AAAA00',
}


def parse_args(args):
    filter_fields = {k: v for k, v in args.items() if k != 'group'}
    group_field = args.get('group', None)
    return filter_fields, group_field


def version_sort_key(vstring):
    parts = vstring.split('-')
    if len(parts) == 1:
        release, = parts
        return (release, 0)
    elif len(parts) == 3:
        release, commit_count, commit_hash = parts
        return (release, int(commit_count))


class GraphView(TemplateView):
    template_name = 'chart.html'
    valid_fields = [
        'pilosa_version',
        'config_index',
        'name'
    ]

    def parse_filter_pairs(self, filter_pairs):
        filter_kwargs = {}
        filter_desc = []
        for k, v in self.filter_pairs.items():
            if k not in self.valid_fields:
                continue

            if v.startswith('='):
                # field==value -> exact match
                v = v[1:]
                filter_suffix = ''
                filter_desc.append("%s == '%s'" % (k, v))
            else:
                # field=value -> contains match
                filter_suffix = '__icontains'
                filter_desc.append("%s contains '%s'" % (k, v))

            filter_kwargs[k+filter_suffix] = v

        return filter_kwargs, filter_desc


class GroupedView(GraphView):
    title = 'Grouped comparison graph'

    def get(self, request, *args, **kwargs):
        self.filter_pairs, self.group_field = parse_args(request.GET)
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(GroupedView, self).get_context_data(**kwargs)
        context['title'] = self.title

        xgroup = 'pilosa_version'  # TODO arbitrary, from query arg
        cgroup = 'config_index'    # color group. TODO arbitrary, from query arg

        # handle filters
        filter_kwargs, desc = self.parse_filter_pairs(self.filter_pairs)

        benchmarks = Benchmark.objects.filter(**filter_kwargs)
        if len(benchmarks) == 0:
            # TODO: indicate 0 results somehow
            return context

        labels = list(set([getattr(b, xgroup) for b in benchmarks]))

        if labels == 'pilosa_version':
            labels.sort(key=version_sort_key)
        else:
            labels.sort()

        # TODO apply cgrouping here

        traces = [go.Scatter(
            x=[labels.index(getattr(b, xgroup)) for b in benchmarks],
            y=[b.stats_mean_us*MICROSEC_TO_SEC for b in benchmarks],
            mode='markers',
        )]

        # setup plot layout/style
        layout = go.Layout(
            title='Grouped (%d results)<br>%s' % (len(benchmarks), ', '.join(desc)),
            xaxis=dict(
                title=xgroup,
                ticktext=labels,
                tickvals=range(len(labels)),
            ),
            yaxis=dict(
                title='Runtime (seconds)',
                type='log',
                autorange=True
            )
        )

        fig = go.Figure(data=traces, layout=layout)
        div = opy.plot(fig, auto_open=False, output_type='div')
        context['graph'] = div

        return context


class TimeseriesView(GraphView):
    title = 'Timeseries graph'

    def get(self, request, *args, **kwargs):
        self.filter_pairs, self.group_field = parse_args(request.GET)
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super(TimeseriesView, self).get_context_data(**kwargs)
        context['title'] = self.title  # main page title

        # handle filters
        filter_kwargs, desc = self.parse_filter_pairs(self.filter_pairs)

        benchmarks = Benchmark.objects.filter(**filter_kwargs)
        if len(benchmarks) == 0:
            # TODO: indicate 0 results somehow
            return context

        benchmarks = benchmarks.order_by('run__pi_build_time')

        # group into dict
        # TODO use ORM?
        if self.group_field:
            desc.append('grouped by %s' % self.group_field)
        trace_dict = {}
        for b in benchmarks:
            key = 'All benchmarks'
            if self.group_field:
                key = getattr(b, self.group_field)

            if key in trace_dict:
                trace_dict[key]['x'].append(b.run.pi_build_time)
                trace_dict[key]['y'].append(b.stats_mean_us*MICROSEC_TO_SEC)
            else:
                trace_dict[key] = go.Scatter(
                    x=[b.run.pi_build_time],
                    y=[b.stats_mean_us*MICROSEC_TO_SEC],
                    name=key,
                    mode='markers',
                )

        # sort the grouping key and extract values into list
        traces = []
        keys = trace_dict.keys()
        if self.group_field == 'pilosa_version':
            keys.sort(key=version_sort_key)
        else:
            keys.sort()

        n = 0
        for key in keys:
            traces.append(trace_dict[key])
            traces[-1]['marker'] = {'color': color_cycle.values()[n]}
            n = (n+1) % len(color_cycle)

        # setup plot layout/style
        layout = go.Layout(
            title='Timeseries (%d results)<br>%s' % (len(benchmarks), ', '.join(desc)),
            xaxis=dict(title='Date'),
            yaxis=dict(
                title='Runtime (seconds)',
                type='log',
                autorange=True
            )
        )

        # return plot object
        fig = go.Figure(data=traces, layout=layout)
        div = opy.plot(fig, auto_open=False, output_type='div')
        context['graph'] = div
        return context


class ChartView(TemplateView):

    template_name = "chart.html"
    title = 'Benchmark plots'

    def get(self, request, *args, **kwargs):
        self.query = request.GET.get('query')
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        if self.query:
            benchmarks = Benchmark.objects.filter(config_index=kwargs.get('slug'), name__icontains=self.query)
        else:
            benchmarks = Benchmark.objects.filter(config_index=kwargs.get('slug'))

        context = super(ChartView, self).get_context_data(**kwargs)
        context['title'] = self.title
        if len(benchmarks) == 0:
            return
        version_map = defaultdict(list)
        for b in benchmarks:
            version_map[b.pilosa_version].append((b.run_id, b.stats_mean_us, b.name))

        if not self.query:
            traces = [go.Box(y=[int(val[1]) for val in version_map[key]],
                             x=[val[2] for val in version_map[key]],
                             name=key,
                             boxpoints='outliers',
                             whiskerwidth=1, ) for key in version_map.keys()]
        else:
            traces = [go.Box(y=[int(val[1]) for val in version_map[key]],
                             x=[val[0] for val in version_map[key]],
                             name=key, boxpoints='outliers',
                             whiskerwidth=0.2, ) for key in version_map.keys()]

        fig = go.Figure(data=traces)
        div = opy.plot(fig, auto_open=False, output_type='div')
        context['graph'] = div
        return context
