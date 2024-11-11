#TODO Add function doctrings.

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ultralytics.engine.results import Results


def get_results_stats(results: list[Results]) -> list[dict]:

    results_stats = []

    for result in results:

        result_stats = {}

        boxes = result.boxes
        masks = result.masks
        keypoints = result.keypoints
        probs = result.probs
        obb = result.obb

        if len(boxes) > 0:
            result_stats["idxs"] = result.boxes.id.tolist()
            result_stats["n_boxes"] = len(boxes)
            result_stats["n_keypoints"] = len(keypoints)

        else:
            result_stats["idxs"] = []
            result_stats["n_boxes"] = 0
            result_stats["n_keypoints"] = 0

        results_stats.append(result_stats)

    return results_stats

def plot_number_detections(results_stats: list[dict]) -> None:
    """
    Desarmar esta función en varias
    """
    n_boxes = [r["n_boxes"] for r in results_stats]
    n_keypoints = [r["n_keypoints"] for r in results_stats]

    px.line(x=range(len(results_stats)), y=n_boxes, title="n_boxes", range_y=[0, max(n_boxes)+5], line_shape='hv', template="plotly_white").show()
    px.line(x=range(len(results_stats)), y=n_keypoints, title="n_keypoints", range_y=[0, max(n_keypoints)+5], line_shape='hv', template="plotly_white").show()


def get_idx_presence_matrix(results_stats: list[dict]) -> pd.DataFrame:
    """
    Crea una matriz de presencia de IDs a lo largo del tiempo.
    """

    idxs_per_step = [[i for i in r["idxs"]] for r in results_stats]
    idxs_per_step = pd.Series(idxs_per_step)
    idx_presence_matrix = pd.get_dummies(idxs_per_step.explode()).groupby(level=0).sum().T.sort_index()

    return idx_presence_matrix


def plot_idx_presence_matrix(idx_presence_matrix: pd.DataFrame) -> None:

    # Creación del heatmap con plotly
    fig = go.Figure(data=go.Heatmap(
            z=idx_presence_matrix.values,
            x=idx_presence_matrix.columns,
            y=idx_presence_matrix.index,
            colorscale='YlGn',
            showscale=False,
            hovertemplate='frame: %{x}<br>idx: %{y}<br>presence: %{z}<extra></extra>'
        ))


    # Personalizar el layout
    fig.update_layout(
        title='Heatmap usando Plotly',
        xaxis_nticks=18,
        yaxis_nticks=10,
        #width=1400,
        height=600,
        xaxis_title="Frame",
        yaxis_title="idx"
    )

    # Mostrar el gráfico
    fig.show()

def plot_detection_stats(results_stats: list[dict]) -> None:

    plot_number_detections(results_stats)

    idx_presence_matrix = get_idx_presence_matrix(results_stats)
    plot_idx_presence_matrix(idx_presence_matrix)