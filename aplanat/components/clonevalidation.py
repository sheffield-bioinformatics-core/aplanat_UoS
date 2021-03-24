"""Report component for displaying information from wf-clone-validation."""
import argparse

from bokeh.layouts import gridplot, layout
from bokeh.models import Div, Panel, Tabs
import markdown
import pandas as pd

from aplanat import base, hist
from aplanat.report import bokeh_table, HTMLReport, HTMLSection
from aplanat.util import Colors


class CloneValidationQC(HTMLSection):
    """Build an aplanat dashboard from wf-clone-validation output."""

    def __init__(
        self,
        assembly_summary,
        assembly_mafs,
        reads_summary,
        fastq_summary
    ) -> None:
        """Load the json file and output the dashboard."""
        super().__init__()
        self.md = markdown.Markdown()
        self.build_report(
            assembly_summary,
            assembly_mafs,
            reads_summary,
            fastq_summary
        )

    def build_report(
        self,
        assembly_summary,
        assembly_mafs,
        reads_summary,
        fastq_summary
    ):
        """Build_report."""
        assemblies = self.build_assemblies_panel(
            assembly_summary, assembly_mafs)
        samples = self.build_samples_panel(
            fastq_summary, reads_summary)

        # Tabula rasa
        panel = Tabs(tabs=[assemblies, samples])
        self.plot(panel)

    def build_assemblies_panel(self, assemblies_file, mafs):
        """Build_assemblies_panel."""
        # Dotplots
        dotplots = []
        for maf in mafs:
            dotplots.append(self.dotplot_assembly(maf))

        text = (
            "This tab contains a basic table of "
            "stats for each final assembly, as well "
            "as dotplots generated by self-alignment. "
            "These dotplots should be a near-perfect "
            "diagonal line if the assembly has worked."
        )
        plots = [
            [self.get_description(text)],
            [Div(text="<br />")],
            [self.build_table(assemblies_file)],
            [gridplot(dotplots, ncols=2)]
        ]

        main = layout(plots, sizing_mode="scale_width")
        panel = Panel(child=main, title="Assemblies")
        return panel

    def build_samples_panel(self, summary_file, reads_file):
        """Build_length_tab."""
        summary_df = pd.read_csv(summary_file, sep="\t")
        reads_df = pd.read_csv(reads_file, sep="\t")

        length_plots = []
        qual_plots = []

        filenames = set(reads_df['filename'].tolist())
        for fname in filenames:
            fname_read = reads_df.loc[reads_df['filename'] == fname]
            fname_summary = summary_df.loc[summary_df['filename'] == fname]
            length_plots.append(self.plot_read_length_distribution(
                fname, int(fname_summary['n_seqs']),
                int(fname_summary['n_bases']),
                int(fname_summary['min_length']),
                int(fname_summary['max_length']), fname_read))
            qual_plots.append(self.plot_qscore_distribution(
                fname, float(fname_summary['mean_quality']), fname_read))

        length_grid = gridplot(
            length_plots, ncols=2,
            sizing_mode="stretch_width")

        quality_grid = gridplot(
            qual_plots, ncols=2,
            sizing_mode="stretch_width")

        text = (
            "This tab contains visualisations of "
            "read length and average quality for "
            "the final, filtered datasets used in assembly, "
            "from each of the samples respectively. I.e, "
            "this is post-host filtering and downsampling."
        )
        plots = [
            [self.get_description(text)],
            [length_grid],
            [quality_grid]
        ]

        main = layout(plots, sizing_mode="scale_width")
        return Panel(child=main, title="Samples")

    def build_table(self, tsv_file):
        """Build the table or get the flake again."""
        df = pd.read_csv(tsv_file, sep='\t')
        plot = bokeh_table(df, index=False)
        plot.height = min(plot.height, 25*(len(df) + 1))
        return plot

    def plot_read_length_distribution(
            self, fname, nseqs, nbases, minl, maxl, data):
        """Plot_read_length_distribution."""
        plot = hist.histogram(
            [data['read_length'].tolist()],
            # bins=1000,
            height=300,
            width=400,
            xlim=(0, max(data['read_length']) + 200),
            colors=[Colors.light_cornflower_blue],
            x_axis_label='Length',
            y_axis_label='Count',
            title=f"{fname}: {nseqs} seqs, {nbases} bp, {minl} min, {maxl} max"
        )

        self.style_plot(plot)
        return plot

    def plot_qscore_distribution(self, fname, mean, data):
        """Plot_qscore_distribution."""
        plot = hist.histogram(
            [data['mean_quality'].tolist()],
            # bins=600,
            height=300,
            width=400,
            xlim=(0, 30),
            colors=[Colors.light_cornflower_blue],
            x_axis_label='Mean Quality',
            y_axis_label='Count',
            title=f"{fname}: {mean} mean q-score"
        )

        self.style_plot(plot)
        return plot

    def style_plot(self, plot):
        """Style plots."""
        plot.margin = (10, 10, 40, 10)
        plot.background_fill_alpha = 0

    def dotplot_assembly(self, assembly_maf):
        """Dotplot the assembly."""
        records = list()
        with open(assembly_maf) as maf:
            while True:
                line = maf.readline()
                print(line)
                if line.startswith('#'):
                    continue
                elif line.startswith('a'):
                    r1 = maf.readline().split()[1:5]
                    r2 = maf.readline().split()[1:5]
                    maf.readline()
                    records.append(r1 + r2)
                elif line == "":
                    break
                else:
                    print(line)
                    raise IOError("Cannot read alignment file")

        names = ['ref', 'rstart', 'rlen', 'rorient',
                 'query', 'qstart', 'qlen', 'qorient']
        df = pd.DataFrame(records, columns=names)
        df = df.loc[df['qorient'] == '+']
        for f in ['qstart', 'qlen', 'rstart', 'rlen']:
            df[f] = df[f].astype(int)
        df['qend'] = df['qstart'] + df['qlen']
        df['rend'] = df['rstart'] + df['rlen']

        df['qend'] = df['qend'].astype(int)
        df['rend'] = df['rend'].astype(int)
        dotplot = base.simple(
            [], [],
            xlim=(0, max(df['rend'])),
            ylim=(0, max(df['qend'])),
            width=440,
            height=400,
            x_axis_label='position',
            y_axis_label='position',
            title=assembly_maf
        )
        dotplot.segment(df['rstart'], df['qstart'], df['rend'], df['qend'])
        return dotplot

    def get_description(self, desc):
        """Get Description."""
        styles = [
            "display:block;",
            "width:100%;",
            "padding:25px 0 0 0;",
            "font-size: 16px;",
            "margin-bottom: 0;"
        ]
        return Div(
            text=f'<p style="{"".join(styles)}" class="lead">{desc}</p>'
        )


def main(args):
    """Entry point to create a wf-clone-validation report."""
    report = HTMLReport(
        title='Clone Validaton',
        lead=(
            "Results generated through the wf-clone-validation "
            "nextflow workflow provided by Oxford Nanopore "
            "Technologies"))
    report.add_section(
        section=CloneValidationQC(
            assembly_summary=args.assembly_summary,
            assembly_mafs=args.assembly_mafs,
            reads_summary=args.reads_summary,
            fastq_summary=args.fastq_summary
        ))
    report.write('report.html')


def argparser():
    """Argument parser for entrypoint."""
    parser = argparse.ArgumentParser(
        'Clone Validation QC report',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=False)

    parser.add_argument(
        "--assembly_summary",
        required=True
    )

    parser.add_argument(
        "--assembly_mafs",
        nargs='*',
        required=True
    )

    parser.add_argument(
        "--reads_summary",
        required=True
    )

    parser.add_argument(
        "--fastq_summary",
        required=True
    )

    return parser
