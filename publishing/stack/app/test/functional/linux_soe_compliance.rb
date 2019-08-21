# Test Linux Compliance

control 'HDA Linux Agent Check 1' do
  title 'Check SSM Agent'
  desc 'SSM Agent should be installed, enabled and running'
  impact 1.0
  require 'rbconfig'
  is_windows = (RbConfig::CONFIG['host_os'] =~ /mswin|mingw|cygwin/)
  if ! is_windows
    describe service 'amazon-ssm-agent' do
      it { should be_installed }
      it { should be_enabled }
      it { should be_running }
    end
  end
end

control 'HDA Linux Agent Check 2' do
  title 'Check Inspector Agent'
  desc 'AWS Inspector Agent should be installed, enabled and running'
  impact 1.0
  require 'rbconfig'
  is_windows = (RbConfig::CONFIG['host_os'] =~ /mswin|mingw|cygwin/)
  if ! is_windows
    describe service 'awsagent' do
      it { should be_installed }
      it { should be_enabled }
      it { should be_running }
    end
  end
end

control 'HDA Linux Agents Check 3' do
  title 'Check CodeDeploy Agent'
  desc 'CodeDeploy Agent should be installed, enabled and running'
  impact 0.7
  require 'rbconfig'
  is_windows = (RbConfig::CONFIG['host_os'] =~ /mswin|mingw|cygwin/)
  if ! is_windows
    describe service 'codedeploy-agent' do
      it { should be_installed }
      it { should be_enabled }
      it { should be_running }
    end
  end
end

control 'HDA Linux Agents Check 4' do
  title 'Check CW Agent'
  desc 'CW Agent should be installed'
  impact 0.8
  require 'rbconfig'
  is_windows = (RbConfig::CONFIG['host_os'] =~ /mswin|mingw|cygwin/)
  if ! is_windows
    describe service 'amazon-cloudwatch-agent' do
      it { should be_installed }
    end
  end
end

control 'HDA Linux Agents Check 5' do
  title 'Check Java Installation'
  desc 'AWS Corretto JRE should be installed'
  impact 0.8
  require 'rbconfig'
  is_windows = (RbConfig::CONFIG['host_os'] =~ /mswin|mingw|cygwin/)
  if ! is_windows
    describe command('java -version') do
      its('exit_status') { should eq 0 }
    end
  end
end

# TODO: enable it when DeepSec is deployed
# control 'HDA Linux Agents Check 5' do
#   title 'Check DeepSec'
#   desc 'DeepSec Agent should be installed, enabled and running'
#   impact 1.0
#   require 'rbconfig'
#   is_windows = (RbConfig::CONFIG['host_os'] =~ /mswin|mingw|cygwin/)
#   if ! is_windows
#     describe service 'someagent' do
#       it { should be_installed }
#       it { should be_enabled }
#       it { should be_running }
#     end
#   end
# end