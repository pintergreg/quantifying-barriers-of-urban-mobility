# frozen_string_literal: true

require 'rqrcode'

qrcode = RQRCode::QRCode.new('https://pintergreg.github.io/quantifying-barriers-of-urban-mobility', level: :q)

svg = qrcode.as_svg(
  color: '#2d2d2d',
  fill: 'ffffff',
  shape_rendering: 'crispEdges',
  offset: 12,
  module_size: 12,
  standalone: true,
  use_path: true
)

File.open('static/images/qr.svg', 'w') { |file| file.write(svg) }
