require "optparse"

options = {}
OptionParser.new do |opts|
    opts.banner = "Usage: pipeline.rb NETWORK\n\nNote that this script expects input network from data/place_connections_2019-09-01_2020-02-29_<NETWORK>.csv"

    opts.on("-n", "--network NETWORK", String, "define network by its identifier, uses default if not specified") do |n|
        options[:network] = n
    end
end.parse!

suffix = ""
if options[:network] and not options[:network].empty?
    suffix = "_" + options[:network]
end
puts  options[:network]

puts " - place_network_louvain"
%x(poetry run python src/place_network_louvain.py --observed-network data/place_connections_2019-09-01_2020-02-29#{suffix}.csv --block data/house_blocks.geojson --community-dir place_communities/#{suffix.gsub("_", "")})

puts " - convert_to_edgelist"
if not suffix.empty?
    %x(poetry run python src/convert_to_edgelist.py --input data/place_connections_2019-09-01_2020-02-29#{suffix}.csv --output output/network/ --suffix #{suffix})
else
    %x(poetry run python src/convert_to_edgelist.py --input data/place_connections_2019-09-01_2020-02-29#{suffix}.csv --output output/network/)
end

puts " - generate_beeline_trips"
%x(poetry run python src/generate_beeline_trips.py --observed observed#{suffix} --blocks data/house_blocks.geojson --network-dir output/network/)

puts " - calculate_barrier_crossings"
%x(poetry run python src/calculate_barrier_crossings.py --network observed#{suffix} --multithreading --pool 2)

puts " - calculate_community_crossings"
%x(poetry run python src/calculate_community_crossings.py --network observed#{suffix} --communities output/place_communities/#{suffix.gsub("_", "")}/louvain --run-stop 10)

puts " - null_model_obs_ratio"
%x(poetry run python src/null_model_obs_ratio.py --barrier-crossing output/barrier_crossing/observed#{suffix} --community-crossing output/community_crossing/observed#{suffix} --output output/obs_ratio/#{suffix.gsub("_", "")}
