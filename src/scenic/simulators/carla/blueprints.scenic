"""CARLA blueprints for cars, pedestrians, etc."""

## Vehicle blueprints

carModels = {# for speed = 10, #Longitudinal: K_P=0.5, K_D=0.1, K_I=0.7 /  # Lateral PID:  K_P=0.3, K_D=0.2, K_I=0
      # 'vehicle.audi.a2', ## not for lanechange
      'vehicle.audi.etron', ## not for lanechange
      'vehicle.audi.tt', ## not for lanechange
      'vehicle.bmw.grandtourer',
      # 'vehicle.bmw.isetta', # current PID controller not work 
      'vehicle.chevrolet.impala',
      'vehicle.citroen.c3',
      'vehicle.dodge_charger.police',
      'vehicle.mustang.mustang',
      # 'vehicle.jeep.wrangler_rubicon',  # current PID controller not work 
      'vehicle.lincoln.mkz2017',
      # 'vehicle.mercedes-benz.coupe',
      # 'vehicle.mini.cooperst',
      'vehicle.nissan.micra',
      'vehicle.nissan.patrol',
      'vehicle.seat.leon',
      'vehicle.tesla.model3', ## not for lanechange
      'vehicle.toyota.prius',
      'vehicle.volkswagen.t2',
      'vehicle.tesla.cybertruck'
}

bicycleModels = {# Speed 10 : Longitudinal : K_P=0.25, K_D=0.025, K_I=0.0 
      'vehicle.bh.crossbike', # Lateral :  K_P=0.2, K_D=0.1, K_I=0.0
      'vehicle.diamondback.century', # Lateral :  K_P=0.2, K_D=0.1, K_I=0.0
      'vehicle.gazelle.omafiets', # Lateral :  K_P=0.2, K_D=0.1, K_I=0.0
}

motorcycleModels = {# Speed 10 : Longitudinal : K_P=0.25, K_D=0.025, K_I=0.0 
      'vehicle.harley-davidson.low_rider', # Lateral :  K_P=0.2, K_D=0.1, K_I=0.0
      'vehicle.kawasaki.ninja', # Lateral :  K_P=0.2, K_D=0.1, K_I=0.0
      'vehicle.yamaha.yzf', # Lateral :  K_P=0.2, K_D=0.1, K_I=0.0
}

truckModels = {# for speed = 10, #Longitudinal: K_P=0.5, K_D=0.1, K_I=0.7 /  # Lateral PID:  K_P=0.3, K_D=0.2, K_I=0
      'vehicle.carlamotors.carlacola',
      'vehicle.tesla.cybertruck'
}

## Prop blueprints

trashModels = {
      'static.prop.trashcan01',
      'static.prop.trashcan02',
      'static.prop.trashcan03',
      'static.prop.trashcan04',
      'static.prop.trashcan05',
      'static.prop.trashbag'
}

coneModels = {
      'static.prop.constructioncone',
      'static.prop.trafficcone01',
      'static.prop.trafficcone02'
}

## Walker blueprints

walkerModels = {
      'walker.pedestrian.0001',
      'walker.pedestrian.0002',
      'walker.pedestrian.0003',
      'walker.pedestrian.0004',
      'walker.pedestrian.0005',
      'walker.pedestrian.0006',
      'walker.pedestrian.0007',
      'walker.pedestrian.0008',
      'walker.pedestrian.0009',
      'walker.pedestrian.0010',
      'walker.pedestrian.0011',
      'walker.pedestrian.0012',
      'walker.pedestrian.0013',
      'walker.pedestrian.0014'
}