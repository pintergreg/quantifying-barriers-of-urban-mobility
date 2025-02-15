require "optparse"

options = {}
OptionParser.new do |opts|
    opts.banner = "Usage: pipeline_libertybridge.rb"

    opts.on("--downtown", "Specify downtown variant") do |x|
        options[:downtown] = true
    end
end.parse!

variant = ""  # empty or downtown
if options[:downtown]
    variant = "downtown"
end

networks = [
    "june_we0",
    "june_we1",
    "june_we2",
    "june_we3",
    "june_we4",
    "szabihid_1",
    "szabihid_2",
    "szabihid_3",
    "szabihid_4",
    ]
targets = [
    "2019-06-01_2019-06-02",
    "2019-06-08_2019-06-09",
    "2019-06-15_2019-06-16",
    "2019-06-22_2019-06-23",
    "2019-06-29_2019-06-30",
    "2019-07-06_2019-07-07",
    "2019-07-13_2019-07-14",
    "2019-07-20_2019-07-21",
    "2019-07-27_2019-07-28",
]
networks.zip(targets).each do |n, target|
    network = "#{n}#{variant.empty? ? "" : "_"}#{variant}"
    input = "place_connections_#{target}#{variant.empty? ? "" : "_"}#{variant}.csv"
    puts network

    puts " - place_network_louvain"
    %x(poetry run python src/place_network_louvain.py --observed-network data/#{input} --block data/house_blocks.geojson --community-dir place_communities/#{network})

    puts " - convert_to_edgelist"
    %x(poetry run python src/convert_to_edgelist.py --input data/#{input} --output output/network/ --suffix _#{network})

    puts " - generate_beeline_trips"
    %x(poetry run python src/generate_beeline_trips.py --observed observed_#{network} --blocks data/house_blocks.geojson --network-dir output/network/)

    puts " - calculate_barrier_crossings"
    %x(poetry run python src/calculate_barrier_crossings.py --network observed_#{network} --multithreading --pool 2)

    puts " - calculate_community_crossings"
    %x(poetry run python src/calculate_community_crossings.py --network observed_#{network} --communities output/place_communities/#{network}/louvain --run-stop 10)

    puts " - null_model_obs_ratio"
    %x(poetry run python src/null_model_obs_ratio.py --barrier-crossing output/barrier_crossing/observed_#{network} --community-crossing output/community_crossing/observed_#{network} --output output/obs_ratio/#{network})
end
