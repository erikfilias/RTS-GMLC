# Libraries
import itertools
import time
import pandas as pd


def GettingDataTo_oTData(_path_data, _path_file, CaseName):
    print('Transforming data to get the oT_Data files ****')

    StartTime = time.time()

    # reading data from the folder SourceData
    df_branch  = pd.read_csv(_path_data + '/SourceData/branch.csv')
    df_bus     = pd.read_csv(_path_data + '/SourceData/bus.csv')
    df_gen     = pd.read_csv(_path_data + '/SourceData/gen.csv')
    df_storage = pd.read_csv(_path_data + '/SourceData/storage.csv')

    # reading data from the folder timeseries_data_file
    df_load    = pd.read_csv(_path_data + '/timeseries_data_files/Load/DAY_AHEAD_regional_Load.csv')
    df_hydro   = pd.read_csv(_path_data + '/timeseries_data_files/Hydro/DAY_AHEAD_hydro.csv')
    df_csp     = pd.read_csv(_path_data + '/timeseries_data_files/CSP/DAY_AHEAD_Natural_Inflow.csv')

    # reading data from the dictionaries
    df_Area          = pd.read_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Dict_Area_'      +CaseName+'.csv')
    df_GenDict       = pd.read_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Dict_Generation_'+CaseName+'.csv')
    df_Node          = pd.read_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Dict_Node_'      +CaseName+'.csv')
    df_NodeToZone    = pd.read_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Dict_NodeToZone_'+CaseName+'.csv')
    df_Period        = pd.read_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Dict_Period_'    +CaseName+'.csv')
    df_Scenario      = pd.read_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Dict_Scenario_'  +CaseName+'.csv')
    df_ZoneToArea    = pd.read_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Dict_ZoneToArea_'+CaseName+'.csv')



    #%% Defining the set 'node to area' and 'area to node'
    ar               = []
    gen              = []
    nd               = []
    ndzn             = []
    znar             = []
    for i in df_Area.index:
        ar.append(df_Area['Area'][i])
    for i in df_GenDict.index:
        gen.append(df_GenDict['Generator'][i])
    for i in df_Node.index:
        nd.append(df_Node['Node'][i])
    for i in df_NodeToZone.index:
        ndzn.append((df_NodeToZone['Node'][i],df_NodeToZone['Zone'][i]))
    for i in df_ZoneToArea.index:
        znar.append((df_ZoneToArea['Zone'][i],df_ZoneToArea['Area'][i]))
    ar   = set(ar)
    gen  = set(gen)
    nd   = set(nd)
    ndzn = set(ndzn)
    znar = set(znar)

    pNode2Area = pd.DataFrame(0, dtype=int, index=pd.MultiIndex.from_tuples(itertools.product(nd, ar), names=('Node', 'Area')), columns=['Y/N'])
    for i,j in ndzn:
        for k in ar:
            if (j,k) in znar:
                pNode2Area['Y/N'][i,k] = 1

    ndar = []
    for i,j in pNode2Area.index:
        if pNode2Area['Y/N'][i,j] == 1:
            ndar.append((i,j))
    ndar = set(ndar)

    #%% Defining the nominal values of the demand per areas
    pNomDemand_org = df_bus[['Bus ID','Area','MW Load']]
    pNomDemArea    = pd.DataFrame(0, dtype=int, index=ar, columns=['MW'])
    for i in ar:
        pNomDemArea['MW'][i] = pNomDemand_org.loc[pNomDemand_org['Area'] == int(i[-1:]), 'MW Load'].sum()

    pNomDemand_org = pNomDemand_org.set_index(['Bus ID'])

    # Defining load levels
    df_load['Month'    ] = df_load.Month.map("{:02}".format)
    df_load['Day'      ] = df_load.Day.map("{:02}".format)
    df_load['Period'   ] = df_load.Period.map("{:02}".format)
    LoadLevels           = [str(df_load['Month'][i])+str(df_load['Day'][i])+str(df_load['Period'][i]) for i in df_load.index]
    df_load['LoadLevel'] = pd.DataFrame({'LoadLevel': LoadLevels})

    # Getting load factors per area
    pDemandPerArea       = df_load.iloc[: ,4 :]
    pDemandPerArea.columns = ['Area_1', 'Area_2', 'Area_3', 'LoadLevel']

    for i in ar:
        pDemandPerArea[i] = pDemandPerArea[i]/pNomDemArea['MW'][i]

    pDemandPerArea = pDemandPerArea.set_index(['LoadLevel'])

    # Defining the pDemand file
    pDemand    = pd.DataFrame(0, dtype=int, index=LoadLevels, columns=sorted(nd))

    # Filling the pDemand file
    for i in LoadLevels:
        for j,k in ndar:
            pDemand.loc[i,j] = pDemandPerArea.loc[i,k] * pNomDemand_org.loc[int(j[-3:]),'MW Load']

    pDemand             = pDemand.reset_index()
    pDemand['Period']   = df_Period.loc  [0, 'Period'  ]
    pDemand['Scenario'] = df_Scenario.loc[0, 'Scenario']

    pDemand = pDemand.set_index(['Period', 'Scenario', 'index'])
    pDemand.rename_axis([None,None,None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_Demand_'+CaseName+'.csv', sep=',', index=True)

    pDemand_File_Time    = time.time() - StartTime
    StartTime            = time.time()
    print('pDemand file  generation               ... ', round(pDemand_File_Time), 's')

    #%% Getting the energy inflows
    df_hydro['LoadLevel'] = pd.DataFrame({'LoadLevel': LoadLevels})
    pHydroInflows         = df_hydro.iloc[: ,4 :]
    pHydroInflows         = pHydroInflows.set_index(['LoadLevel'])
    pHydroInflows         = pHydroInflows.replace(0, 0.0001)

    df_csp['LoadLevel']   = pd.DataFrame({'LoadLevel': LoadLevels})
    pCSPInflows           = df_csp.iloc[: ,4 :]
    pCSPInflows           = pCSPInflows.set_index(['LoadLevel'])
    pCSPInflows           = pCSPInflows.replace(0,0.0001)

    pEnergyInflows        = pd.DataFrame(0, dtype=int, index=LoadLevels, columns=sorted(gen))

    for i in pHydroInflows.columns:
        pEnergyInflows.loc[:,i] = pHydroInflows.loc[:,i]

    for i in pCSPInflows.columns:
        pEnergyInflows.loc[:, i] = pCSPInflows.loc[:,i]

    pEnergyInflows             = pEnergyInflows.reset_index()
    pEnergyInflows['Period']   = df_Period.loc  [0, 'Period'  ]
    pEnergyInflows['Scenario'] = df_Scenario.loc[0, 'Scenario']

    pEnergyInflows = pEnergyInflows.set_index(['Period', 'Scenario', 'index'])
    pEnergyInflows.rename_axis([None,None,None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_EnergyInflows_'+CaseName+'.csv', sep=',', index=True)

    pEnergyInflows_File_Time    = time.time() - StartTime
    StartTime                   = time.time()
    print('pEnergyInflows  file  generation       ... ', round(pEnergyInflows_File_Time), 's')

    #%% Getting the energy outflows
    pEnergyOutflows             = pd.DataFrame(0, dtype=int, index=LoadLevels, columns=sorted(gen))
    pEnergyOutflows             = pEnergyOutflows.reset_index()
    pEnergyOutflows['Period']   = df_Period.loc  [0, 'Period'  ]
    pEnergyOutflows['Scenario'] = df_Scenario.loc[0, 'Scenario']

    pEnergyOutflows = pEnergyOutflows.set_index(['Period', 'Scenario', 'index'])
    pEnergyOutflows.rename_axis([None,None,None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_EnergyOutflows_'+CaseName+'.csv', sep=',', index=True)

    pEnergyOutflows_File_Time   = time.time() - StartTime
    StartTime                   = time.time()
    print('pEnergyOutflows file  generation       ... ', round(pEnergyOutflows_File_Time), 's')

    #%% Generating the oT_Data_Generation file
    # Parameters all units
    pGeneration = pd.DataFrame(0, dtype=int, index=df_gen.index,
                               columns=['Gen', 'Node', 'Technology', 'MutuallyExclusive', 'StorageType', 'OutflowsType',
                                        'MustRun', 'BinaryCommitment', 'NoOperatingReserve', 'InitialPeriod',
                                        'FinalPeriod', 'MaximumPower', 'MinimumPower', 'MaximumCharge',
                                        'MinimumCharge', 'InitialStorage', 'MaximumStorage', 'MinimumStorage',
                                        'Efficiency', 'ShiftTime', 'EFOR', 'RampUp', 'RampDown', 'UpTime', 'DownTime',
                                        'FuelCost', 'LinearTerm', 'ConstantTerm', 'OMVariableCost', 'OperReserveCost',
                                        'StartUpCost', 'ShutDownCost', 'CO2EmissionRate', 'Availability',
                                        'FixedInvestmentCost', 'FixedChargeRate', 'BinaryInvestment', 'Inertia',
                                        'FixedRetirementCost', 'BinaryRetirement', 'MaximumReactivePower',
                                        'MinimumReactivePower', 'InvestmentLo', 'InvestmentUp', 'RetirementLo',
                                        'RetirementUp'])

    pGeneration['MutuallyExclusive'  ] = ""
    pGeneration['StorageType'        ] = ""
    pGeneration['OutflowsType'       ] = ""
    pGeneration['MustRun'            ] = ""
    pGeneration['BinaryCommitment'   ] = ""
    pGeneration['NoOperatingReserve' ] = ""
    pGeneration['FixedInvestmentCost'] = ""
    pGeneration['FixedChargeRate'    ] = ""
    pGeneration['BinaryInvestment'   ] = ""
    pGeneration['FixedRetirementCost'] = ""
    pGeneration['BinaryRetirement'   ] = ""


    for i in pGeneration.index:
        pGeneration.loc[i,'Node'] = 'N_'+str(df_gen.loc[i,'Bus ID'])

    pGeneration['Gen'        ] = df_gen['GEN UID']
    pGeneration['Technology' ] = df_gen['Fuel'   ]

    for i in pGeneration.index:
        if pGeneration.loc[i,'Technology'] == 'Hydro':
            pGeneration.loc[i,'StorageType' ] = 'Weekly'
            pGeneration.loc[i,'OutflowsType'] = 'Weekly'
        if pGeneration.loc[i,'Gen'] == '212_CSP_1' or pGeneration.loc[i,'Technology'] == 'Storage':
            pGeneration.loc[i,'StorageType' ] = 'Daily'
            pGeneration.loc[i,'OutflowsType'] = 'Daily'
        if pGeneration.loc[i, 'Technology'] == 'Nuclear':
            pGeneration.loc[i,'MustRun'] = 'yes'
        if pGeneration.loc[i,'Technology'] == 'Oil' or pGeneration.loc[i,'Technology'] == 'Coal' or pGeneration.loc[i,'Technology'] == 'NG' or pGeneration.loc[i,'Technology'] == 'Nuclear':
            pGeneration.loc[i,'BinaryCommitment'] = 'yes'
        if pGeneration.loc[i, 'Technology'] == 'Solar' or pGeneration.loc[i,'Technology'] == 'Wind':
            pGeneration.loc[i,'NoOperatingReserve'] = 'yes'

    pGeneration['InitialPeriod'    ] = 2015
    pGeneration['FinalPeriod'      ] = 2050
    pGeneration['MaximumPower'     ] = df_gen['PMax MW'                ]
    pGeneration['MinimumPower'     ] = df_gen['PMin MW'                ]
    # Parameters for all thermal units
    pGeneration['EFOR'             ] = df_gen['FOR'                    ]
    pGeneration['RampUp'           ] = df_gen['Ramp Rate MW/Min'       ]*60
    pGeneration['RampDown'         ] = df_gen['Ramp Rate MW/Min'       ]*60
    pGeneration['UpTime'           ] = df_gen['Min Up Time Hr'         ]
    pGeneration['DownTime'         ] = df_gen['Min Down Time Hr'       ]
    pGeneration['FuelCost'         ] = df_gen['Fuel Price $/MMBTU'     ]
    pGeneration['LinearTerm'       ] = df_gen['HR_avg_0'               ]*1000/1000000
    pGeneration['StartUpCost'      ] = df_gen['Start Heat Cold MBTU'   ]*1000*df_gen['Fuel Price $/MMBTU']/1000000
    pGeneration['CO2EmissionRate'  ] = df_gen['Emissions CO2 Lbs/MMBTU']*pGeneration['LinearTerm']*0.0004535924

    # Availability
    for i in pGeneration.index:
        if pGeneration.loc[i,'Technology'] == 'Oil' or pGeneration.loc[i,'Technology'] == 'Coal' or pGeneration.loc[i,'Technology'] == 'NG':
            pGeneration.loc[i,'Availability'] = 0.966
        if pGeneration.loc[i,'Technology'] == 'Nuclear':
            pGeneration.loc[i, 'Availability'] = 0.22275641
        if pGeneration.loc[i,'Technology'] == 'Hydro':
            pGeneration.loc[i, 'Availability'] = 0.339
        if pGeneration.loc[i,'Technology'] == 'Solar':
            pGeneration.loc[i, 'Availability'] = 0.32
        if pGeneration.loc[i,'Technology'] == 'Hydro':
            pGeneration.loc[i, 'Availability'] = 0.01
        if pGeneration.loc[i,'Technology'] == 'Storage':
            pGeneration.loc[i, 'Availability'] = 0.31

    # Parameters for all storage units
    df_storage  = df_storage.set_index(['GEN UID'])
    df_gen      = df_gen.set_index(['GEN UID'])
    pGeneration = pGeneration.set_index(['Gen'])
    for i in df_storage.index:
        # if pGeneration.loc[i,'Technology'] != 'Hydro':
        #     pGeneration.loc[i,'MaximumCharge'] = pGeneration.loc[i,'MaximumPower']
        pGeneration.loc[i,'MaximumCharge'] = df_gen.loc[i,'Pump Load MW']
        pGeneration.loc[i,'Efficiency'   ] = df_gen.loc[i,'Storage Roundtrip Efficiency']/100
        if pGeneration.loc[i, 'Technology'] != 'Storage':
            pGeneration.loc[i,'MaximumStorage'] = df_storage.loc[i,'Max Volume GWh']
            pGeneration.loc[i,'InitialStorage'] = df_storage.loc[i,'Initial Volume GWh']
        else:
            pGeneration.loc[i,'MaximumStorage'] = 0.15
            pGeneration.loc[i,'InitialStorage'] = 0.075
        pGeneration.loc[i, 'MinimumStorage'] = 0

    pGeneration.rename_axis([None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_Generation_'+CaseName+'.csv', sep=',', index=True)

    pGeneration_File_Time = time.time() - StartTime
    StartTime             = time.time()
    print('pGeneration     file  generation       ... ', round(pGeneration_File_Time), 's')

    #%% Generating the Inertia file
    pInertia             = pd.DataFrame(0, dtype=int, index=LoadLevels, columns=sorted(ar))
    pInertia             = pInertia.reset_index()
    pInertia['Period']   = df_Period.loc  [0, 'Period'  ]
    pInertia['Scenario'] = df_Scenario.loc[0, 'Scenario']

    pInertia = pInertia.set_index(['Period', 'Scenario', 'index'])
    pInertia.rename_axis([None,None,None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_Inertia_'+CaseName+'.csv', sep=',', index=True)

    pInertia_File_Time = time.time() - StartTime
    StartTime          = time.time()
    print('pInertia        file  generation       ... ', round(pInertia_File_Time), 's')

    #%% Generating the oT_Data_Network file
    pNetwork = pd.DataFrame(dtype=int, index=df_branch.index,
                               columns=['InitialNode', 'FinalNode', 'Circuit', 'Length', 'LineType', 'InitialPeriod',
                                        'FinalPeriod', 'Voltage', 'LossFactor', 'Resistance', 'Reactance',
                                        'Susceptance', 'Tap', 'TTC', 'TTCBck', 'SecurityFactor', 'FixedInvestmentCost',
                                        'FixedChargeRate', 'BinaryInvestment', 'Switching', 'SwOnTime', 'SwOffTime',
                                        'AngMin', 'AngMax', 'InvestmentLo', 'InvestmentUp'])

    for i in df_branch.index:
        pNetwork.loc[i,'InitialNode'] = 'N_'+str(df_branch.loc[i,'From Bus'])
        pNetwork.loc[i,'FinalNode'  ] = 'N_'+str(df_branch.loc[i,'To Bus'  ])
        if df_branch.loc[i,'Tr Ratio'] == 0:
            pNetwork.loc[i, 'Tap'] = 1
        else:
            pNetwork.loc[i, 'Tap'] = df_branch.loc[i,'Tr Ratio']

    aux_1 = []
    for i in pNetwork.index:
        if (pNetwork.loc[i,'InitialNode'],pNetwork.loc[i,'FinalNode']) not in aux_1:
            pNetwork.loc[i, 'Circuit'] = 'eac'+ str(1)
        else:
            pNetwork.loc[i, 'Circuit'] = 'eac' + str(aux_1.count((pNetwork.loc[i,'InitialNode'],pNetwork.loc[i,'FinalNode']))+1)
        aux_1.append((pNetwork.loc[i,'InitialNode'],pNetwork.loc[i,'FinalNode']))

    pNetwork['Length'             ] = ""
    pNetwork['InitialPeriod'      ] =  2015
    pNetwork['FinalPeriod'        ] =  2050
    pNetwork['LossFactor'         ] =  0.01
    pNetwork['Resistance'         ] = df_branch['R'          ]
    pNetwork['Reactance'          ] = df_branch['X'          ]
    pNetwork['Susceptance'        ] = df_branch['B'          ]
    pNetwork['TTC'                ] = df_branch['Cont Rating']
    pNetwork['TTCBck'             ] = ""
    pNetwork['SecurityFactor'     ] = 1
    pNetwork['FixedInvestmentCost'] = ""
    pNetwork['FixedChargeRate'    ] = ""
    pNetwork['BinaryInvestment'   ] = ""
    pNetwork['Switching'          ] = ""
    pNetwork['SwOnTime'           ] = ""
    pNetwork['SwOffTime'          ] = ""
    pNetwork['AngMin'             ] = -1.047197551
    pNetwork['AngMax'             ] =  1.047197551

    pBus = df_bus.set_index(['Bus ID'])
    for i in pNetwork.index:
        if pNetwork.loc[i,'Susceptance'] == 0:
            pNetwork.loc[i, 'LineType'] = 'DC'
        else:
            pNetwork.loc[i, 'LineType'] = 'AC'
        a = pBus.loc[df_branch.loc[i,'From Bus'], 'BaseKV']
        b = pBus.loc[df_branch.loc[i,'To Bus'  ], 'BaseKV']
        pNetwork.loc[i, 'Voltage'] = max(a,b)

    pNetwork.set_index(['InitialNode','FinalNode','Circuit']).rename_axis([None,None,None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_Network_'+CaseName+'.csv', sep=',', index=True)

    pNetwork_File_Time = time.time() - StartTime
    StartTime          = time.time()
    print('pNetwork        file  generation       ... ', round(pNetwork_File_Time), 's')

    #%% Generating the NodeLocation file
    pNodeLocation      = pd.DataFrame(dtype=int, index=df_bus.index, columns=['Bus','Latitude','Longitude'])
    pNodeLocation['Bus'      ] = sorted(nd)
    pNodeLocation['Latitude' ] = df_bus['lat']
    pNodeLocation['Longitude'] = df_bus['lng']

    pNodeLocation.set_index(['Bus']).rename_axis([None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_NodeLocation_'+CaseName+'.csv', sep=',', index=True)

    pNodeLocation_File_Time = time.time() - StartTime
    StartTime               = time.time()
    print('pNodeLocation   file  generation       ... ', round(pNodeLocation_File_Time), 's')

    #%% Generating the Operating Reserves file
    pOperatingReservesDown              = pd.DataFrame(0, dtype=int, index=LoadLevels, columns=sorted(ar))
    pOperatingReservesDown             = pOperatingReservesDown.reset_index()
    pOperatingReservesDown['Period']   = df_Period.loc  [0, 'Period'  ]
    pOperatingReservesDown['Scenario'] = df_Scenario.loc[0, 'Scenario']

    pOperatingReservesDown = pOperatingReservesDown.set_index(['Period', 'Scenario', 'index'])
    pOperatingReservesDown.rename_axis([None,None,None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_OperatingReservesDown_'+CaseName+'.csv', sep=',', index=True)

    pOperatingReservesDown_File_Time = time.time() - StartTime
    StartTime          = time.time()
    print('pOperReservDown file  generation       ... ', round(pOperatingReservesDown_File_Time), 's')

    pOperatingReservesUp             = pd.DataFrame(0, dtype=int, index=LoadLevels, columns=sorted(ar))
    pOperatingReservesUp             = pOperatingReservesUp.reset_index()
    pOperatingReservesUp['Period']   = df_Period.loc  [0, 'Period'  ]
    pOperatingReservesUp['Scenario'] = df_Scenario.loc[0, 'Scenario']

    pOperatingReservesUp = pOperatingReservesUp.set_index(['Period', 'Scenario', 'index'])
    pOperatingReservesUp.rename_axis([None,None,None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_OperatingReservesUp_'+CaseName+'.csv', sep=',', index=True)

    pOperatingReservesUp_File_Time = time.time() - StartTime
    StartTime          = time.time()
    print('pOperReservUp   file  generation       ... ', round(pOperatingReservesUp_File_Time), 's')

    #%% Generating the Option file
    pOption = pd.DataFrame(0, dtype=int, index=pd.Index(['Options']), columns=['IndBinGenInvest', 'IndBinGenRetirement',
                                                                   'IndBinNetInvest', 'IndBinGenOperat',
                                                                   'IndBinNetLosses', 'IndBinLineCommit',
                                                                   'IndBinSingleNode', 'IndBinGenRamps',
                                                                   'IndBinGenMinTime'])

    pOption['IndBinGenOperat' ] = 0
    pOption['IndBinSingleNode'] = 0
    pOption['IndBinGenRamps'  ] = 1
    pOption['IndBinGenMinTime'] = 1

    pOption.rename_axis([None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_Option_'+CaseName+'.csv', sep=',', index=True)

    pOption_File_Time  = time.time() - StartTime
    StartTime          = time.time()
    print('pOption         file  generation       ... ', round(pOption_File_Time), 's')

    #%% Generating the Parameter file
    pParameter = pd.DataFrame(0, dtype=int, index=pd.Index(['Parameters']),
                              columns=['ENSCost', 'CO2Cost','AnnualDiscountRate', 'UpReserveActivation',
                                       'DwReserveActivation', 'MinRatioDwUp','MaxRatioDwUp', 'EconomicBaseYear',
                                       'SBase','ReferenceNode','TimeStep'])

    pParameter['ENSCost' ] = 10000
    pParameter['CO2Cost'] = 70
    pParameter['AnnualDiscountRate'  ] = 0.04
    pParameter['UpReserveActivation'] = 0.25
    pParameter['DwReserveActivation'] = 0.3
    pParameter['MinRatioDwUp'] = 0
    pParameter['MaxRatioDwUp'] = 1
    pParameter['EconomicBaseYear'] = 2020
    pParameter['SBase'] = 100
    pParameter['TimeStep'] = 1

    for i in df_bus.index:
        if df_bus.loc[i,'Bus Type'] == 'Ref':
            a = 'N_'+str(df_bus.loc[i,'Bus ID'])

    pParameter['ReferenceNode'] = a

    pParameter.rename_axis([None], axis=0).to_csv(_path_file+'/openTEPES_RTS-GMLC/oT_Data_Parameter_'+CaseName+'.csv', sep=',', index=True)

    pParameter_File_Time = time.time() - StartTime
    StartTime            = time.time()
    print('pParameter      file  generation       ... ', round(pParameter_File_Time), 's')

    
