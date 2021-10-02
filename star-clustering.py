import os
import pandas as pd
import scipy.cluster.hierarchy as sch
from scipy.spatial.distance import pdist
from sklearn.cluster import AgglomerativeClustering
import numpy as np
import plotly.graph_objects as go
from sklearn.metrics import pairwise_distances
from plotly.figure_factory import create_dendrogram


# pd.options.plotting.backend = "plotly"

# calculates the distance on a sphere, ra and dec must be in degrees
def sphere_distance(p1, p2):
    ra1 = p1[0] * 360 / 24
    dec1 = p1[1]
    ra2 = p2[0] * 360 / 24
    dec2 = p2[1]

    distance = np.cos(np.deg2rad(90 - dec1)) * np.cos(np.deg2rad(90 - dec2)) + np.sin(np.deg2rad(90 - dec1)) * np.sin(
        np.deg2rad(90 - dec2)) * np.cos(np.deg2rad(ra1 - ra2))

    if distance > 1:
        distance = 1

    distance = np.degrees(np.arccos(distance))
    if distance < 0:
        print("Negative distance")

    return distance


def calc_dist_by_id(id1, id2):
    point1 = df.loc[df['id'] == id1, ["ra", "dec"]].iloc[0]
    point2 = df.loc[df['id'] == id2, ["ra", "dec"]].iloc[0]

    print(sphere_distance(point1, point2))


def scale(val, src, dst):
    """
    Scale the given value from the scale of src to the scale of dst.
    """
    return ((val - src[0]) / (src[1] - src[0])) * (dst[1] - dst[0]) + dst[0]

df = pd.read_csv(r'database_root.csv', low_memory=False)

# Milano è 45°28′01″N 9°11′24″E

print("Initial shape: ", df.shape)

df = df[df["dec"] > 0]

unnamed = df[pd.isnull(df['proper'])]
unnamed = unnamed[unnamed["mag"] < 7]

df = df[~pd.isnull(df['proper'])]
# df["proper"].fillna('no name')
# df = df[df["mag"] < 6]


print("Filtered named star: ", df.shape)

df = pd.concat([df, unnamed[unnamed["mag"] < 3.5]])

print("Final shape: ", df.shape)

sizes = []

for index, item in df.iterrows():
    size = scale(
        item["mag"],
        [max(df["mag"]), min(df["mag"])],
        [.05, 4]
    )
    sizes.append(size)

# df.insert(0, "opacity", opacities)
df.insert(0, "size", sizes)

distance_threshold = 12

ac = AgglomerativeClustering(
    n_clusters=None,
    distance_threshold=distance_threshold,
    affinity=lambda X: pairwise_distances(X, metric=sphere_distance),
    linkage='single'
)

# TODO Differenza tra fit e fit_predict?
ac.fit(df.loc[:, ["ra", "dec"]])

print(max(ac.labels_ + 1), "costellazioni")

# Associa a ciascun index dei dati, il cluster di appartenenza
clustered_data = pd.DataFrame([df.index, ac.labels_]).T

colors = [
    "red",
    "green",
    "yellow"
]

grouped_indexes = clustered_data.groupby(1)

# Inizializza la figura
fig = go.Figure()
for label in range(grouped_indexes.ngroups):
    indexes = grouped_indexes.groups[label]

    filtered = df.iloc[indexes]

    # filtered["mag"].apply(lambda x: float(x))

    fig.add_trace(go.Scatterpolar(
        r=filtered['dec'],
        theta=[datum['ra'] * 360 / 24 for index, datum in filtered.iterrows()],
        mode='markers',
        text=[str(item["id"]) + " " + str(item["proper"]) for i, item in filtered.iterrows()],

        marker=dict(
            # color=colors[label],
            # symbol="square",
            # opacity=filtered["opacity"],
            # size=5 - np.log(4 - filtered["mag"]),
            opacity=1,
            size=filtered["size"],
            line=dict(
                width=0
            )
        )
    ))

fig.update_layout(polar=dict(
    # Inverte l'asse dec
    radialaxis=dict(range=[90, 0]),
    bgcolor='#384554',
    # angularaxis=dict(showticklabels=False, ticks='')
))

fig.show()

if not os.path.exists("images"):
    os.mkdir("images")

fig.write_image("images/scatterpolar.svg")

# Dendrogram
dendro = create_dendrogram(
    df.loc[:, ["ra", "dec"]],
    color_threshold=distance_threshold,
    distfun=lambda x: pdist(x, metric=sphere_distance),
    linkagefun=lambda x: sch.linkage(x, "single"),
    labels=[item["proper"] if not pd.isnull(item["proper"]) else item["id"] for i, item in df.iterrows()]
)

dendro.update_layout({'width': 1400, 'height': 900})
dendro.show()
dendro.write_image("images/dendrogram.svg")
