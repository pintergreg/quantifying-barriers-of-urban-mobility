import re
import os
import subprocess

for f in os.listdir("data/group"):
    g = os.path.basename(str(f))
    i = re.search("place_connections_2019-09-01_2020-02-29_([a-z_]+)\.csv", g).group(1)
    print(i)

    cte = f"poetry run python src/convert_to_edgelist.py --input data/group/{g} --output output/network/ --suffix _{i}"
    subprocess.call(cte, shell=True)

    gbt = f"poetry run python src/generate_beeline_trips.py --observed observed_{i} --blocks data/house_blocks.geojson --network-dir output/network/"
    subprocess.call(gbt, shell=True)

    cbc = f"poetry run python src/calculate_barrier_crossings.py --network observed_{i}"
    subprocess.call(cbc, shell=True)

    amtoem = f"poetry run python src/add_movements_to_empty_mesh.py --input data/group/{g} --observed-trips output/trips/network_observed_{i}_beeline.pickle.gz --output output/mesh_final_{i}.csv --observed-barrier-crossing-dir output/barrier_crossing/observed_{i}"
    # subprocess.call(amtoem, shell=True)
    # subprocess.call(f"gzip output/mesh_final_{i}.csv", shell=True)

    cd = f"poetry run python src/place_network_louvain.py --observed-network data/group/place_connections_2019-09-01_2020-02-29_{i}.csv --block data/house_blocks.geojson --community-dir place_communities/{i}"
    subprocess.call(cd, shell=True)

    ccc = f"poetry run python src/calculate_community_crossings.py --network observed_{i} --communities output/place_communities/{i}/louvain/ --run-stop 10"
    subprocess.call(ccc, shell=True)

    nmor = f"poetry run python src/null_model_obs_ratio.py --barrier-crossing output/barrier_crossing/observed_{i} --community-crossing output/community_crossing/observed_{i} --output output/obs_ratio/{i}"
    subprocess.call(nmor, shell=True)
