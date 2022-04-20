require 'json'
require 'pry'

class Comparer
	attr_reader :prod_data, :merged_data, :staging_data
	def initialize
=begin
		@prod_data 	= JSON.parse(File.read('first_import/sentry_export_production.json'))
		@staging_data = JSON.parse(File.read('first_import/sentry_export_staging.json'))
		@merged_data 		= JSON.parse(File.read('02-16-2022.13.26.01_merged_export.json'))
=end
		@prod_data 	= JSON.parse(File.read('second_import/second_do_sentry_export_production.json'))
		@staging_data = JSON.parse(File.read('second_import/second_do_sentry_export_staging.json'))
		@merged_data 		= JSON.parse(File.read('03-07-2022.11.54.35_merged_export.json'))
	end

	def compare
		compare_teams
		compare_projects
		compare_projectoptions_rules_keys
	end

	def compare_teams
		prod_teams = prod_data.select{|entry| entry['model'] == 'sentry.team'}
		staging_teams = staging_data.select{|entry| entry['model'] == 'sentry.team'}
		merged_teams = merged_data.select{|entry| entry['model'] == 'sentry.team'}
		found_teams = {}

		prod_teams.each do |prod_team|
			prod_slug = prod_team['fields']['slug']
			found_teams[prod_slug] = false
			merged_teams.each do |merged_team|
				merged_slug = merged_team['fields']['slug']
				if found_teams[prod_slug]
					next
				elsif prod_slug == merged_slug
					found_teams[prod_slug] = true
					next
				end
			end
		end

		staging_teams.each do |staging_team|
			staging_slug = staging_team['fields']['slug']
			found_teams[staging_slug] = false
			merged_teams.each do |merged_team|
				merged_slug = merged_team['fields']['slug']
				if found_teams[staging_slug]
					next
				elsif staging_slug == merged_slug
					found_teams[staging_slug] = true
					next
				end
			end
		end

		found_teams.each do |slug, _|
			if !found_teams[slug]
				raise "did not find slug #{slug}"
			end
		end
		puts "Teams compared and successfully merged: #{merged_teams.size}"
		puts "----------------------------"
	end

	def compare_projects
		prod_projects = prod_data.select{|entry| entry['model'] == 'sentry.project'}
		staging_projects = staging_data.select{|entry| entry['model'] == 'sentry.project'}
		merged_projects = merged_data.select{|entry| entry['model'] == 'sentry.project'}
		found_projects = {}

 		prod_projects.each do |prod_project|
			prod_slug = prod_project['fields']['slug']
			found_projects[prod_slug] = false
			merged_projects.each do |merged_project|
				merged_slug = merged_project['fields']['slug']
				if found_projects[prod_slug]
					next
				elsif prod_slug == merged_slug
					found_projects[prod_slug] = true
					next
				end
			end
		end

		found_projects.each do |slug, _|
			if !found_projects[slug]
				raise "did not find slug #{slug}"
			end
		end
		puts "Projects compared and successfully merged: #{merged_projects.size}"
		puts "----------------------------"
	end

	# select all projects in prod
	# for each proj, use the pk to select associated project options (select ['fields']['project'] == proj_pk)
	#
	# do the same for staging
	# 
	# do the same for merged
	# 
	# for each prod_proj
	#   find the associated merged project by comparing slugs
	#   for each of their projectoptions, compare the ['field']['value']
	def compare_projectoptions_rules_keys
		prod_projects = prod_data.select{|entry| entry['model'] == 'sentry.project'}
		staging_projects = staging_data.select{|entry| entry['model'] == 'sentry.project'}
		merged_projects = merged_data.select{|entry| entry['model'] == 'sentry.project'}

		prod_mapping = []
		prod_projects.each do |prod_proj|
			associated_vals = {}
			options = prod_data.select{|entry| entry['model'] == 'sentry.projectoption' && entry['fields']['project'] == prod_proj['pk']}
			rules = prod_data.select{|entry| entry['model'] == 'sentry.rule' && entry['fields']['project'] == prod_proj['pk']}
			keys = prod_data.select{|entry| entry['model'] == 'sentry.projectkey' && entry['fields']['project'] == prod_proj['pk']}
			associated_vals[prod_proj['fields']['slug']] = {
				options: options,
				rules: rules,
				keys: keys
			}
			prod_mapping << associated_vals
		end

		staging_mapping = []
		staging_projects.each do |staging_proj|
			associated_vals = {}
			options = staging_data.select{|entry| entry['model'] == 'sentry.projectoption' && entry['fields']['project'] == staging_proj['pk']}
			rules = staging_data.select{|entry| entry['model'] == 'sentry.rule' && entry['fields']['project'] == staging_proj['pk']}
			keys = staging_data.select{|entry| entry['model'] == 'sentry.projectkey' && entry['fields']['project'] == staging_proj['pk']}
			associated_vals[staging_proj['fields']['slug']] = {
				options: options,
				rules: rules,
				keys: keys
			}
			staging_mapping << associated_vals
		end

		merged_mapping = []
		merged_projects.each do |merged_proj|
			associated_vals = {}
			options = merged_data.select{|entry| entry['model'] == 'sentry.projectoption' && entry['fields']['project'] == merged_proj['pk']}
			rules = merged_data.select{|entry| entry['model'] == 'sentry.rule' && entry['fields']['project'] == merged_proj['pk']}
			keys = merged_data.select{|entry| entry['model'] == 'sentry.projectkey' && entry['fields']['project'] == merged_proj['pk']}
			associated_vals[merged_proj['fields']['slug']] = {
				options: options,
				rules: rules,
				keys: keys
			}
			merged_mapping << associated_vals
		end


		########################################
		########################################
		##### COMPARE OPTIONS ##################
		########################################
		########################################

		merged_options = merged_data.select{|entry| entry['model'] == 'sentry.projectoption'}

		prod_mapping.each do |data_prod|
			slug_prod = data_prod.first.first
			equivalent_merged_project_data = merged_mapping.find{|merged_proj| merged_proj.first.first == slug_prod}[slug_prod]
			data_prod[slug_prod][:options].each do |prod_opt|
				matched_opt = equivalent_merged_project_data[:options].find{|merged_opt| prod_opt['fields']['value'] == merged_opt['fields']['value']}
				if !matched_opt
					raise "Could not match project options for project #{slug_prod}"
				end
			end
		end

		staging_mapping.each do |data_staging|
			slug_staging = data_staging.first.first
			if prod_mapping.find{|data_prod| data_prod[slug_staging]}
				next
			end
			# puts "Unique staging project #{slug_staging}"
			equivalent_merged_project_data = merged_mapping.find{|merged_proj| merged_proj.first.first == slug_staging}[slug_staging]
			data_staging[slug_staging][:options].each do |staging_opt|
				matched_opt = equivalent_merged_project_data[:options].find{|merged_opt| staging_opt['fields']['value'] == merged_opt['fields']['value']}
				if !matched_opt
					raise "Could not match project options for project #{slug_staging}"
				end
			end
		end

		puts "Projectoptions compared and successfully merged: #{merged_options.size}"
		puts "----------------------------" 

		########################################
		########################################
		##### COMPARE RULES ####################
		########################################
		########################################

		merged_rules = merged_data.select{|entry| entry['model'] == 'sentry.rule'}

		prod_mapping.each do |data_prod|
			slug_prod = data_prod.first.first
			equivalent_merged_project_data = merged_mapping.find{|merged_proj| merged_proj.first.first == slug_prod}[slug_prod]
			data_prod[slug_prod][:rules].each do |prod_rule|
				matched_rule = equivalent_merged_project_data[:rules].find{|merged_rule| prod_rule['fields']['value'] == merged_rule['fields']['value']}
				if !matched_rule
					raise "Could not match Rules for project #{slug_prod}"
				end
			end
		end

		staging_mapping.each do |data_staging|
			slug_staging = data_staging.first.first
			if prod_mapping.find{|data_prod| data_prod[slug_staging]}
				next
			end
			# puts "Unique staging project #{slug_staging}"
			equivalent_merged_project_data = merged_mapping.find{|merged_proj| merged_proj.first.first == slug_staging}[slug_staging]
			data_staging[slug_staging][:rules].each do |staging_rule|
				matched_rule = equivalent_merged_project_data[:rules].find{|merged_rule| staging_rule['fields']['value'] == merged_rule['fields']['value']}
				if !matched_rule
					raise "Could not match Rules for project #{slug_staging}"
				end
			end
		end

		puts "Rules compared and successfully merged: #{merged_rules.size}"
		puts "----------------------------" 

		########################################
		########################################
		##### COMPARE KEYS #####################
		########################################
		########################################

		merged_keys = merged_data.select{|entry| entry['model'] == 'sentry.projectkey'}


		prod_mapping.each do |data_prod|
			slug_prod = data_prod.first.first
			equivalent_merged_project_data = merged_mapping.find{|merged_proj| merged_proj.first.first == slug_prod}[slug_prod]
			data_prod[slug_prod][:keys].each do |prod_key|
				matched_key = equivalent_merged_project_data[:keys].find{|merged_key| prod_key['fields']['value'] == merged_key['fields']['value']}
				if !matched_key
					raise "Could not match project keys for project #{slug_prod}"
				end
			end
		end

		staging_mapping.each do |data_staging|
			slug_staging = data_staging.first.first
			if prod_mapping.find{|data_prod| data_prod[slug_staging]}
				next
			end
			# puts "Unique staging project #{slug_staging}"
			equivalent_merged_project_data = merged_mapping.find{|merged_proj| merged_proj.first.first == slug_staging}[slug_staging]
			data_staging[slug_staging][:keys].each do |staging_key|
				matched_key = equivalent_merged_project_data[:keys].find{|merged_key| staging_key['fields']['value'] == merged_key['fields']['value']}
				if !matched_key
					raise "Could not match project keys for project #{slug_staging}"
				end
			end
		end

		puts "Project Keys compared and successfully merged: #{merged_keys.size}"
		puts "----------------------------" 
	end
end

Comparer.new.compare
