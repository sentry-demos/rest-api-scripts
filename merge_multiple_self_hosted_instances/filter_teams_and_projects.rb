require 'json'
require 'pry'

class Filterer
  attr_reader :raw_staging, :raw_prod, :all_projects, :raw_legacy

  def initialize
=begin
    @raw_staging     = JSON.parse(File.read('second_import/second_do_sentry_export_staging.json'))
    @raw_prod        = JSON.parse(File.read('second_import/second_do_sentry_export_production.json'))
    @all_projects = fetch_projects
=end
    @raw_staging     = JSON.parse(File.read('fs/sentry-export-uat-adjusted.json'))
    @raw_prod        = JSON.parse(File.read('fs/sentry-export-prod.json'))
    @raw_legacy      = JSON.parse(File.read('fs/sentry-export-fio-adjusted.json'))
    @all_projects = fetch_projects
  end

  def combine_data
    puts "-------------------------"
    puts "Separating teams"
    puts "-------------------------"
    teams = separated_teams
    team_slugs = teams[:only_prod] + teams[:only_staging] + teams[:both_prod_and_staging] + teams[:legacy_instance]
    team_slugs = team_slugs.uniq
    teams = full_team_data(team_slugs)
    pk_standardized_teams = standardize_pk_team_data(teams)

    puts "-------------------------"
    puts "Separating projects"
    puts "-------------------------"
    projects = separated_projects
    project_slugs = separated_projects[:only_prod] + separated_projects[:only_staging] + separated_projects[:both_prod_and_staging] + separated_projects[:legacy_instance]
    puts "-------------------------"
    puts "Getting projects and associated values"
    puts "-------------------------"
    projects = get_projects_and_associated_values(project_slugs)
        binding.pry

    pk_standardized_projects = standardize_pk_project_data(projects)
    binding.pry
    
    if !pks_standardized_corrrectly(pk_standardized_projects)
      # only projectoptions are tested here -- as a spot check
      raise 'Project PKs were not standardized correctly across projectoptions'
    end


    # edit: i don't think i need to add staging-only teams back in, this is complete already i believe
    ##############################################
    ##############################################
    ##############################################
    #### #TODO: add staging-only teams back in! ##
    ##############################################
    ##############################################
    ##############################################

    final_export = raw_prod

    puts "Before removing from prod..."
    puts "Number of teams: #{final_export.select{|entry| entry['model'] == 'sentry.team'}.size}"
    puts "Number of projects: #{final_export.select{|entry| entry['model'] == 'sentry.project'}.size}"
    puts "Number of project options: #{final_export.select{|entry| entry['model'] == 'sentry.projectoption'}.size}"
    puts "Number of rules: #{final_export.select{|entry| entry['model'] == 'sentry.rule'}.size}"
    puts "Number of keys: #{final_export.select{|entry| entry['model'] == 'sentry.projectkey'}.size}"
    puts "--------------------------------------------"


    final_export = final_export.reject do |entry|
      ['sentry.team', 'sentry.project', 'sentry.projectoption', 'sentry.rule', 'sentry.projectkey'].include?(entry['model'])
    end

    puts "After removing from prod..."
    puts "Number of teams: #{final_export.select{|entry| entry['model'] == 'sentry.team'}.size}"
    puts "Number of projects: #{final_export.select{|entry| entry['model'] == 'sentry.project'}.size}"
    puts "Number of project options: #{final_export.select{|entry| entry['model'] == 'sentry.projectoption'}.size}"
    puts "Number of rules: #{final_export.select{|entry| entry['model'] == 'sentry.rule'}.size}"
    puts "Number of keys: #{final_export.select{|entry| entry['model'] == 'sentry.projectkey'}.size}"
    puts "--------------------------------------------"

    pk_standardized_projects.each do |project_data|
      final_export << project_data[:project]

      project_data[:options].each do |option|
        final_export << option
      end

      project_data[:rules].each do |rule|
        final_export << rule
      end

      project_data[:keys].each do |key|
        final_export << key
      end
    end

    binding.pry

    # binding.pry
    pk_standardized_teams.each do |team_data|
      final_export << team_data
    end

    puts "After populating with merged staging/prod..."
    puts "Number of teams: #{final_export.select{|entry| entry['model'] == 'sentry.team'}.size}"
    puts "Number of projects: #{final_export.select{|entry| entry['model'] == 'sentry.project'}.size}"
    puts "Number of project options: #{final_export.select{|entry| entry['model'] == 'sentry.projectoption'}.size}"
    puts "Number of rules: #{final_export.select{|entry| entry['model'] == 'sentry.rule'}.size}"
    puts "Number of keys: #{final_export.select{|entry| entry['model'] == 'sentry.projectkey'}.size}"


    current_time = Time.now.strftime("%m-%d-%Y.%H.%M.%S")
    File.open("#{current_time}_merged_export.json", "w") do |f|
      f.write(final_export.to_json)
    end

    # afterwards can use the comparer.rb file in same directory here to
    # programmatically check that the merge was successful
  end

  private

  def human_readable_staging(field_type, unique_identifying_field)
    matching = raw_staging.select{|entry| entry['model'] == field_type}
    matching.map do |v|
      v['fields'][unique_identifying_field]
    end
  end

  def human_readable_prod(field_type, unique_identifying_field)
    matching = raw_prod.select{|entry| entry['model'] == field_type}
    matching.map do |v|
      v['fields'][unique_identifying_field]
    end
  end

  def human_readable(data, field_type, unique_identifying_field)
    matching = data.select{|entry| entry['model'] == field_type}
    matching.map do |v|
      v['fields'][unique_identifying_field]
    end
  end

  def separated_teams
    separate_values('sentry.team', 'slug')
  end

  def separated_projects
    @separated_projects ||= separate_values('sentry.project', 'slug')
  end

  def separate_values(field_type, unique_identifying_field)
    both_prod_and_staging = []
    only_staging = []
    only_prod = []

    all_staging = human_readable(raw_staging, field_type, unique_identifying_field)
    all_prod    = human_readable(raw_prod, field_type, unique_identifying_field)

    all_prod.each do |field|
      if all_staging.include?(field)
        both_prod_and_staging << field
      else
        only_prod << field
      end
    end

    all_staging.each do |field|
      if !both_prod_and_staging.include?(field)
        only_staging << field
      end
    end
    # end

    aggregate = {
      field_type: field_type,
      unique_identifying_field: unique_identifying_field,
      both_prod_and_staging: both_prod_and_staging,
      only_staging: only_staging,
      only_prod: only_prod,
      legacy_instance: human_readable(raw_legacy, field_type, unique_identifying_field)
    }

    puts "-----------------"
    puts "Field: #{field_type}"
    puts "ONLY staging count: #{aggregate[:only_staging].size}"
    puts "ONLY prod count: #{aggregate[:only_prod].size}"
    puts "BOTH prod and staging count: #{aggregate[:both_prod_and_staging].size}"
    puts "LEGACY INSTANCE count: #{aggregate[:legacy_instance].size}"
    puts "total count: #{aggregate[:only_prod].size + aggregate[:legacy_instance].size + aggregate[:only_staging].size}"
    puts "TOTAL unique count: #{aggregate[:only_prod].size + aggregate[:only_staging].size + aggregate[:both_prod_and_staging].size + aggregate[:legacy_instance].size}"
    # binding.pry
    return aggregate
  end

  def full_team_data(team_slugs)
    team_slugs.map do |team_slug|
      prod_teams = raw_prod.select{|datum| datum['model'] == 'sentry.team'}
      staging_teams = raw_staging.select{|datum| datum['model'] == 'sentry.team'}
      legacy_teams = raw_legacy.select{|datum| datum['model'] == 'sentry.team'}
      
      # try to find slug in prod
      prod_record = prod_teams.find{|team| team['fields']['slug'] == team_slug}
      staging_record = staging_teams.find{|team| team['fields']['slug'] == team_slug}
      legacy_record = legacy_teams.find{|team| team['fields']['slug'] == team_slug}

      if prod_record
        prod_record
      elsif staging_record
        staging_record
      elsif legacy_record
        legacy_record
      else
        raise "could not find record for team: #{team_slug}" #shouldn't happen
      end
    end
  end

  # snippet to confirm that all the pks were updated successfully
  def pks_standardized_corrrectly(pk_standardized_projects)
    mismatched = pk_standardized_projects.select do |project|
      pk = project[:project]['pk']
      project[:options].select do |option|
        option['fields']['project'] != pk
      end.size > 1
    end
    mismatched.empty?
  end

  # standardize all the project-pk (primary key) values for
  # each project, and its associated options/rules/keys
  def standardize_pk_project_data(projects)
    proj_count    = 1
    options_count = 1
    rules_count   = 1
    keys_count    = 1

    projects.map do |project|
      project = project
      project[:project]['pk'] = proj_count

      project[:options].each do |option|
        option['pk'] = options_count
        option['fields']['project'] = proj_count
        options_count += 1
      end

      project[:rules].each do |rule|
        rule['pk'] = rules_count
        rule['fields']['project'] = proj_count
        rules_count += 1
      end

      project[:keys].each do |key|
        key['pk'] = keys_count
        key['fields']['project'] = proj_count
        keys_count += 1
      end

      proj_count += 1
      project
    end
  end

  # standardize all the team-pk (primary key) values for
  # each project, and its associated options/rules/keys
  def standardize_pk_team_data(teams)
    team_count    = 1

    teams.map do |team|
      team = team
      team['pk'] = team_count

      team_count += 1
      team
    end
  end

  def get_projects_and_associated_values(project_slugs)
    puts "Projects count: #{project_slugs.size}"
    count = 0
    binding.pry
    projects  = project_slugs.map do |slug|
      project = get_project_data(slug)

      options = fetch_projectoptions(project)
      rules   = fetch_rules(project)
      keys    = fetch_keys(project)
      puts count
      count += 1
      {
        project: project,
        options: options,
        rules: rules,
        keys: keys
      }
    end
  end

  ################################
  #### find the projectoptions ###
  ################################
  def fetch_projectoptions(project)
    prod_projectoptions     = prod_values('sentry.projectoption')
    staging_projectoptions  = staging_values('sentry.projectoption')
    legacy_projectoptions   = legacy_values('sentry.projectoption')

    project_pk = project['pk']
    if project['environment'] == 'prod'
      return options = prod_projectoptions.select{|po| po['fields']['project'] == project_pk}
    elsif project['environment'] == 'staging'
      return options = staging_projectoptions.select{|po| po['fields']['project'] == project_pk}
    elsif project['environment'] == 'legacy'
      return options = legacy_projectoptions.select{|po| po['fields']['project'] == project_pk}
    else
      raise "should not hit this. project slug #{project['fields']['slug']}"
    end
  end

  ################################
  #### find the rules  ###########
  ################################
  def fetch_rules(project)
    prod_rules = prod_values('sentry.rule')
    staging_rules = staging_values('sentry.rule')
    legacy_rules = legacy_values('sentry.rule')
    
    project_pk = project['pk']
    if project['environment'] == 'prod'
      return prod_rules.select{|rule| rule['fields']['project'] == project_pk}
    elsif project['environment'] == 'staging'
      return staging_rules.select{|rule| rule['fields']['project'] == project_pk}
    elsif project['environment'] == 'legacy'
      return legacy_rules.select{|rule| rule['fields']['project'] == project_pk}
    else
      raise "should not hit this. project slug #{project['fields']['slug']}"
    end
  end

  ######################################
  #### find the projectkeys  ###########
  ######################################
  def fetch_keys(project)
    prod_keys = prod_values('sentry.projectkey')
    # binding.pry
    staging_keys = staging_values('sentry.projectkey')
    legacy_keys = legacy_values('sentry.projectkey')
    
    # It's important to differentiate prod and staging projects here.
    # Otherwise we end up selecting overlapping options for both prod and staging and cause bugs
    project_pk = project['pk']
    if project['environment'] == 'prod'
      keys = prod_keys.select{|key| key['fields']['project'] == project_pk && key['environment'] == 'prod'}
    elsif project['environment'] == 'staging'
      keys = staging_keys.select{|key| key['fields']['project'] == project_pk && key['environment'] == 'staging'}
    elsif project['environment'] == 'legacy'
      keys = legacy_keys.select{|key| key['fields']['project'] == project_pk && key['environment'] == 'legacy'}
    else
      raise "should not hit this. project slug #{project['fields']['slug']}"
    end
  end

  def prod_values(field_type)
    vals = raw_prod.select{|entry| entry['model'] == field_type}
    vals.map do |val|
      val['environment'] = 'prod'
      val
    end
  end

  def staging_values(field_type)
    vals = raw_staging.select{|entry| entry['model'] == field_type}
    vals.map do |val|
      val['environment'] = 'staging'
      val
    end
  end

  def legacy_values(field_type)
    vals = raw_legacy.select{|entry| entry['model'] == field_type}
    vals.map do |val|
      val['environment'] = 'legacy' ################ todo: ask Nick what he wants the "environment" to be loaded as for each instance? or not
      val
    end
  end

  def fetch_projects
    staging_projects  = raw_staging.select{|h| h['model'] == 'sentry.project'}
    prod_projects     = raw_prod.select{|h| h['model'] == 'sentry.project'}
    legacy_projects   = raw_legacy.select{|h| h['model'] == 'sentry.project'}
    {
      staging: staging_projects,
      prod: prod_projects,
      legacy: legacy_projects
    }
  end

  def get_project_data(slug)
    prod_record = all_projects[:prod].find{|p| p['fields']['slug'] == slug}
    staging_record = all_projects[:staging].find{|p| p['fields']['slug'] == slug}
    legacy_record = all_projects[:legacy].find{|p| p['fields']['slug'] == slug}

    if slug == 'econ-estimate-comparison'
      binding.pry
    end

    # if the project exists in prod as well as staging, prioritize prod version
    if prod_record
      prod_record['environment'] = 'prod'
      return prod_record
    elsif staging_record
      staging_record['environment'] = 'staging'
      return staging_record
    elsif legacy_record
      legacy_record['environment'] = 'legacy'
      return legacy_record
    else
      binding.pry
      raise "Project neither in prod nor staging nor legacy (this should not happen): #{slug}"
    end
  end
end

Filterer.new.combine_data
