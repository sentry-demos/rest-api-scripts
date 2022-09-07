require 'json'
require 'pry'

class TeamFixer
	attr_reader :prod_data, :merged_data, :staging_data, :legacy_data
	def initialize
		@merged_data 		= JSON.parse(File.read('fs-08-17-2022.15.47.59_merged_export.json'))
	end

	def fix
		final_export = merged_data.map do |entry|
			if entry['model'] == 'sentry.team' || entry['model'] == 'sentry.project'
				entry['fields']['organization'] = 1
			end

			if entry['model'] == 'sentry.project' && !entry['fields'].keys.include?('platform')
				binding.pry
				entry['fields']['platform'] = nil
				binding.pry
			end

			entry
		end

		current_time = Time.now.strftime("%m-%d-%Y.%H.%M.%S")
    File.open("#{current_time}_merged_export.json", "w") do |f|
      f.write(final_export.to_json)
    end
	end
end

TeamFixer.new.fix
