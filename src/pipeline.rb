networks = ["high_complexity_half"]
networks.each do |network|
    puts network

    puts " - place_network_louvain"
    %x(poetry run python src/place_network_louvain.py --observed-network data/place_connections_2019-09-01_2020-02-29_#{network}.csv --block data/house_blocks.geojson --community-dir place_communities/#{network})

    puts " - convert_to_edgelist"
    %x(poetry run python src/convert_to_edgelist.py --input data/place_connections_2019-09-01_2020-02-29_#{network}.csv --output output/network/ --suffix _#{network})

    puts " - generate_beeline_trips"
    %x(poetry run python src/generate_beeline_trips.py --observed observed_#{network} --blocks data/house_blocks.geojson --network-dir output/network/)

    puts " - calculate_barrier_crossings"
    %x(poetry run python src/calculate_barrier_crossings.py --network observed_#{network} --multithreading --pool 2)

    puts " - calculate_community_crossings"
    %x(poetry run python src/calculate_community_crossings.py --network observed_#{network} --communities output/place_communities/#{network}/louvain --run-stop 10)

    puts " - null_model_obs_ratio"
    %x(poetry run python src/null_model_obs_ratio.py --barrier-crossing output/barrier_crossing/observed_#{network} --community-crossing output/community_crossing/observed_#{network} --output output/obs_ratio/#{network})


    puts " - calculate_community_crossings with full network communities"
    %x(poetry run python src/calculate_community_crossings.py --network observed_#{network} --communities output/place_communities/louvain --run-stop 10 --output output_orig/community_crossing/)

    puts " - null_model_obs_ratio with full network communities"
    %x(poetry run python src/null_model_obs_ratio.py --barrier-crossing output/barrier_crossing/observed_#{network} --community-crossing output_orig/community_crossing/observed_#{network} --output output_orig/obs_ratio/#{network})
end
