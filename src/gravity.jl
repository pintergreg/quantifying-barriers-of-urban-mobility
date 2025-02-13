using Dates, CSV, DataFrames, GLM, RegressionTables, FixedEffectModels, ArgParse

function save_model_tables(models, filename)
    regtable(models...; renderSettings = asciiOutput("$(filename).txt"))
    regtable(models...; renderSettings = latexOutput("$(filename).tex"))
end;

function save_result(model, filename)
    open(filename, "w") do file
        show(file, model)
    end
end;

function read_mesh(path; columns=nothing)
    println("start loading mesh")
    df = DataFrame(CSV.File("$(path)"; select=columns, types=Float64))
    println("mesh loaded")

    filter!(row -> row[:source] != row[:target], df)
    println("mesh filtered")

    return df
end;

function fit_model1(df, output)
    model = reg(df, @formula(mob_ij ~ p_i + p_j + distance_ij))
    save_result(model, "$(output)/model1.txt")
    println("model 1 OK")
    return model
end

function fit_model2(df, output)
    model = reg(df, @formula(mob_ij ~ p_i + p_j + distance_ij + primary_count))
    save_result(model, "$(output)/model2.txt")
    println("model 2 OK")
    return model
end

function fit_model3(df, output)
    model = reg(df, @formula(mob_ij ~ p_i + p_j + distance_ij + secondary_count))
    save_result(model, "$(output)/model3.txt")
    println("model 3 OK")
    return model
end

function fit_model4(df, output)
    model = reg(df, @formula(mob_ij ~ p_i + p_j + distance_ij + railway_count))
    save_result(model, "$(output)/model4.txt")
    println("model 4 OK")
    return model
end

function fit_model5(df, output)
    model = reg(df, @formula(mob_ij ~ p_i + p_j + distance_ij + river_count))
    save_result(model, "$(output)/model5.txt")
    println("model 5 OK")
    return model
end

function fit_model6(df, output)
    model = reg(df, @formula(mob_ij ~ p_i + p_j + distance_ij + districts_count))
    save_result(model, "$(output)/model6.txt")
    println("model 6 OK")
    return model
end

function fit_model7(df, output)
    model = reg(df, @formula(mob_ij ~ p_i + p_j + distance_ij + neighborhoods_count))
    save_result(model, "$(output)/model7.txt")
    println("model 7 OK")
    return model
end;

function fit_modelb(df, output)
    model = reg(df, @formula(mob_ij ~ p_i + p_j + distance_ij + primary_count + secondary_count + railway_count + river_count + districts_count + neighborhoods_count))
    save_result(model, "$(output)/modelb.txt")
    println("model B OK")
    return model
end;

function fit_models_sep(df, output)
    m1 = fit_model1(df, output)
    m2 = fit_model2(df, output)
    m3 = fit_model3(df, output)
    m4 = fit_model4(df, output)
    m5 = fit_model5(df, output)
    m6 = fit_model6(df, output)
    m7 = fit_model7(df, output)

    save_model_tables([m1, m2, m3, m4, m5, m6, m7], "$(output)/gravity_models_1-7")
end;

function fit_models(path, output)
    fit_model1(read_mesh(path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij"]), output)
    fit_model2(read_mesh(path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "primary_count"]), output)
    fit_model3(read_mesh(path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "secondary_count"]), output)
    fit_model4(read_mesh(path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "railway_count"]), output)
    fit_model5(read_mesh(path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "river_count"]), output)
    fit_model6(read_mesh(path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "districts_count"]), output)
    fit_model7(read_mesh(path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "neighborhoods_count"]), output)
end;

function parse_commandline()
    s = ArgParseSettings()

    @add_arg_table! s begin
        "--mesh"
            help = "path for enriched mesh"
            default = "output/mesh_final.csv"
        "--output"
            help = "output directory"
            default = "output/ols"
    end

    return parse_args(s)
end;

function main()
    opts = parse_commandline()
    output = strip(opts["output"])
    mesh_path = strip(opts["mesh"])
    mkpath(output)  # parent=True, exists_ok=True by default
    df = read_mesh(mesh_path,)
    fit_models_sep(df, output)
    fit_modelb(df, output)

    # fit_model1(read_mesh(mesh_path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij"]), output)
    # fit_model2(read_mesh(mesh_path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "primary_count"]), output)
    # fit_model3(read_mesh(mesh_path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "secondary_count"]), output)
    # fit_model4(read_mesh(mesh_path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "railway_count"]), output)
    # fit_model5(read_mesh(mesh_path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "river_count"]), output)
    # fit_model6(read_mesh(mesh_path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "districts_count"]), output)
    # fit_model7(read_mesh(mesh_path, columns=["source", "target", "distance_ij", "p_i", "p_j", "mob_ij", "neighborhoods_count"]), output)
    # fit_modelb(read_mesh(mesh_path), output)
end;

main()
