#!/home/sho/bin/ruby18
#!/usr/bin/env ruby
#
# amazon-auth-proxy.rb:
#	Authentication Proxy Server of Amazon Product Advertising API.
#
# Copyright (C) 2009 TADA Tadashi <t@tdtds.jp>
# You can redistribute it and/or modify it under GPL2.
#

require 'uri'
require 'base64'
require 'digest/sha2'
require 'time'
require 'timeout'
require 'open-uri'
require 'erb'
include ERB::Util

module HMAC
	IPAD = "\x36" * 64
	OPAD = "\x5c" * 64

	module_function

	def sha256( key, message )
		ikey = IPAD.dup
		okey = OPAD.dup
		key.size.times do |i|
			ikey[i] = key[i] ^ IPAD[i]
			okey[i] = key[i] ^ OPAD[i]
		end

		value = Digest::SHA256.digest( ikey + message )
		value = Digest::SHA256.digest( okey + value )
	end
end

def paapi( conf, params )
	qs = [].tap {|q|
		params.each do |key, values|
			if key =~ /^(AWSAccessKeyId|SubscriptionId)$/
				q << "#{u key}=#{u conf['access_key']}"
			elsif key == 'Timestamp'
				# ignore this key
			else
				q << "#{u key}=#{u values[0]}"
			end
		end
		unless params.keys.include?( 'AssociateTag' ) then
			q << "AssociateTag=#{u conf['default_aid']}"
		end
		q << "Timestamp=#{u DateTime.now.new_offset.strftime('%Y-%m-%dT%XZ') }"
	}.sort

	uri = URI.parse( conf['entry_point'] )
	message = ['GET', uri.host, uri.path, qs * '&'] * "\n"
	begin
		require 'openssl'
		hash = OpenSSL::HMAC::digest( OpenSSL::Digest::SHA256.new, conf['secret_key'], message )
	rescue LoadError
		hash = HMAC::sha256( conf['secret_key'], message )
	end
	qs << "Signature=#{u [hash].pack( "m" ).chomp}"

	url = uri.to_s + '?' + qs * '&'

	timeout( 10 ) do
		open( url, &:read )
	end
end

if __FILE__ == $0 then
	require 'cgi'
	cgi = CGI::new
	
	require 'yaml'
	conf = YAML::load_file( 'amazon-auth-proxy.yaml' )

	begin
		header = cgi.header(
			'status' => '200',
			'type' => 'text/xml;charset="UTF-8"'
		)
		body = paapi( conf, cgi.params )
		print header
		print body
	rescue
		print "Status: 500\nContent-Type: text/plain\n\n"
		print $!.message
	end
end

