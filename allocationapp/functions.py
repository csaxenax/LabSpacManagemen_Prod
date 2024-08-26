# Deallocate Bench based on WW
"""
STEP 1: Calculate current Workweek for today's date.
STEP 2: Get all the Lab's
STEP3: Get all allocation data with status = allocated
STEP 4: if ToWW expires next week , trigger a mail.
STEP 5: 
"""
from datetime import date
from datetime import datetime
import calendar,os
from django.db.models import Q
from .models import AllocationDetailsModel,LabModel,UserModel
from .mail import Email,ExpiryEmail,CountConfirmation
import aiohttp,json,asyncio,traceback
import logging
logger = logging.getLogger(__name__)
schedular_logger = logging.getLogger('scheduler_logger')
# processed_allocations = set()

def calculate_workweek():
    """
    Returns workweek for the given date
    Args:
        today: date for which workweek has to be calculated
    Returns:
        Workweek : Workweek of the given date

    """
    today = datetime.today()
    Workweek = today.strftime("%V")
    return Workweek

def DeallocationSchedular():
    print("Scheduler started")
    schedular_logger.info("Scheduler Started")
    FROM = 'LabSpaceManager@intel.com'
    cc_query = UserModel.objects.filter(Role__role_name='Admin').values()
    #TO = [each_query['Email'] for each_query in to_query]
    CC = []
    TO = []
    Workweek = calculate_workweek()
    year = date.today().isocalendar()[0]
    current_workweek = str(Workweek)+str(year)
    if int(Workweek)-1 < 10:
        previous_workweek = "0"+str(int(Workweek)-1)+str(year)
    else:
        previous_workweek = str(int(Workweek)-1)+str(year)
    if int(Workweek)+1 <10:
        next_workweek = "0"+str(int(Workweek)+1) + str(year)
    else:
        next_workweek = str(int(Workweek)+1) + str(year)
    try:
        allocation_data = AllocationDetailsModel.objects.filter(status='allocated').values('id','Program','Sku','Vendor','FromWW',"Function",'Department',
            'ToWW','Duration','AllocatedTo','NumberOfbenches','Remarks','Team','IsAllocated','IsRequested','Location__Name','BenchData','AllocatedDate','status','DeallocatedBy')
        #changes,
        summary_data_list = []
        if allocation_data:
            for each_allocation in allocation_data:
                if each_allocation['ToWW'] == "":
                    fromw = int(each_allocation['FromWW'][0:2])  
                    fromw += 1 
                    fromw = str(fromw)  
                    yea = each_allocation['FromWW'][2:]  
                    yea = str(yea)
                    workw = fromw + yea  
                    each_allocation['ToWW'] = str(workw)
                year_part = previous_workweek[-4:]
                week_part = previous_workweek[:-4]
            
                # Convert the string to an integer and subtract 1 to get the previous week
                previous_week_int = int(week_part) - 1
                previous_week_int = 52 if previous_week_int == 0 else previous_week_int
                previous_workweek_1 = f"{previous_week_int:02d}{year_part}"
                
                # if (each_allocation['ToWW'] == "252024"):
                if (each_allocation['ToWW'] == current_workweek) or \
                    (each_allocation['ToWW'] == previous_workweek_1) or \
                        (each_allocation['ToWW'] == previous_workweek) or \
                            (int(each_allocation['ToWW'][2:]) < int(year)) or \
                                ((int(each_allocation['ToWW'][2:]) == int(year)) and (int(each_allocation['ToWW'][:2]) < int(current_workweek[:2]))):
                    # if each_allocation['id'] in processed_allocations:
                    #         continue
                    # processed_allocations.add(each_allocation['id'])
                #     # If allocation expiry workweek is current week
                    current_allocation = AllocationDetailsModel.objects.get(id=each_allocation['id'])
                    current_allocation.status="complete"
                    current_allocation.IsAllocated=False
                    current_allocation.Reason="Allocation Completed successfully"
                    #changes
                    current_allocation.DeallocatedBy = "Automated Deallocation"
                    current_allocation.deallocatedDate = datetime.now()
                    current_allocation.save()
                    benchdata = current_allocation.BenchData
                    lab_query = LabModel.objects.get(Q(Name=current_allocation.Location.Name))
                    for each_bench_request in current_allocation.BenchData:
                        print("each_bench",each_bench_request)
                        if '-' in each_bench_request:  # Check if it's in the format "Rack 7-Shelf 2"
                                rack_label, shelf_label = each_bench_request.split('-')  # Split bench data into rack and shelf labels
                                for each_bench_row in lab_query.BenchDetails:
                                    for each_bench_column in each_bench_row['seats']:
                                        if each_bench_column['labelNo'] == rack_label:
                                            print("each_bench_column",each_bench_column)
                                            if 'RackDetail' in each_bench_column:
                                                for rack_detail in each_bench_column['RackDetail']:
                                                    print("rackdetail",rack_detail)
                                                    if rack_detail['shelfNo'] == shelf_label:
                                                        rack_detail['IsRequested'] = False
                                                        rack_detail['IsAllocated'] = False
                                                        rack_detail['AllocationData'] = None
                                                        print("updated detail",rack_detail)
                                                all_rack_benches_allocated = all(detail['IsAllocated'] for detail in each_bench_column['RackDetail'])
                                                all_rack_benches_requested = all(detail['IsRequested'] for detail in each_bench_column['RackDetail'])
                                                each_bench_column['IsAllocated'] = all_rack_benches_allocated
                                                
                                                each_bench_column['IsRequested'] = all_rack_benches_requested
                                            
                                lab_query.save()    
                        else:
                            for each_bench_row in lab_query.BenchDetails:
                                for each_bench_column_no in range(len(each_bench_row['seats'])):
                                    if each_bench_row['seats'][each_bench_column_no]['labelNo'] == each_bench_request:
                                        print("label_no",each_bench_request)
                                        each_bench_row['seats'][each_bench_column_no]['IsRequested'] = False
                                        each_bench_row['seats'][each_bench_column_no]['IsAllocated'] = False
                                        each_bench_row['seats'][each_bench_column_no]['AllocationData'] = None
                            lab_query.save()
                    try:
                        notify_persons = []
                        if  current_allocation.NotifyTo is not None:     
                            notify_persons =[ current_allocation.NotifyTo[each_person_no]['Name'] for each_person_no in range(len(current_allocation.NotifyTo))]
                            notify_emails = [current_allocation.NotifyTo[each_person_no]['Email'] for each_person_no in range(len(current_allocation.NotifyTo))]
                        else:
                            notify_emails = []
                            notify_persons = []
                    except Exception as e:
                        print(e)
                        
                    # print("number of benches",current_allocation.NumberOfbenches)
                    # print("allocated to",current_allocation.AllocatedTo)
                    # print("benchdata",current_allocation.BenchData)
                    # print("duration",current_allocation.Duration)
                    message = "This email is a confirmation of your Lab Bench <b>Deallocated<b>"
                    subject = "Bench request Deallocated for "
                    mail_data = {
                                "User":current_allocation.AllocatedTo[0]['Name'],
                                "WWID":current_allocation.AllocatedTo[0]['WWID'],
                                "program":current_allocation.Program,
                                "sku":current_allocation.Sku,
                                "lab_name":current_allocation.Location.Name,
                                "vendor":current_allocation.Vendor,
                                "allocatedto":current_allocation.AllocatedTo[0]['Name'],
                                "notifyto":','.join(notify_persons),
                                "requestedBy": current_allocation.RequestedBy[0]['Name'],
                                "fromww":str(current_allocation.FromWW),
                                "toww":str(current_allocation.ToWW),
                                "duration":current_allocation.Duration,
                                "remarks":current_allocation.Remarks,
                                "team":current_allocation.Team,
                                "function":current_allocation.Function,
                                'department':current_allocation.Department,
                                "id":current_allocation.id,
                                "numberofbenches":current_allocation.NumberOfbenches,
                                "message":message,
                                "subject":subject,
                                "deallocatedby":current_allocation.DeallocatedBy,
                            }
                    
                    bench_data = []
                    rack_shelf_data = []
                    if "BenchData" in current_allocation.__dict__ and current_allocation.BenchData:
                        for each_bench in current_allocation.BenchData:
                            if 'Rack' in each_bench:
                                    rack_shelf_data.append(each_bench)
                            else:
                                    bench_data.append(each_bench)
                    mail_data["bench_data"] = bench_data
                    mail_data["Rack-Shelf"] = rack_shelf_data

                    TO.append(' '+str(current_allocation.AllocatedTo[0]['Email']))
                    if notify_emails:
                        Cc = notify_emails
                    else:
                        Cc = []
                    Cc = Cc + CC
                    mail = Email(FROM,TO,Cc,mail_data)
                    mail.sendmail()
                    TO.pop()
                    #mail 
                    # message1 = "LabManagement Deallocation summary report"
                    # subject1 = "Summary "
                    # summary_data_list.append({
                    #         'AllocatedTo': current_allocation.AllocatedTo[0]['Name'],
                    #         'ToWW': str(current_allocation.ToWW),
                    #         'Duration': current_allocation.Duration,
                    #         'ID': current_allocation.id,
                    #         'NumberOfBenches': current_allocation.NumberOfbenches,
                    #         'BenchData': current_allocation.BenchData,
                    #         "fromww":str(current_allocation.FromWW),
                    #         "lab_name":current_allocation.Location.Name,
                    #         "message":message1,
                    #         "subject":subject1,
                    #         # Add other relevant fields as needed
                    #             })
                    # mail = ReportEmail(FROM, "arbazx.ali@intel.com","sakthirajanx.sembulingam@intel.com",summary_data_list)
                    # mail.sendmail()                    

                    schedular_logger.info(f"Bench Deallocated for id {each_allocation['id']}, \
                    User {current_allocation.AllocatedTo[0]['Name']} for benches {current_allocation.BenchData}")
                elif each_allocation['ToWW'] == next_workweek:
                    # If allocation expiry workweek is current week
                    # if each_allocation['id'] in processed_allocations:
                    #     continue
                    # processed_allocations.add(each_allocation['id'])
                    current_allocation = AllocationDetailsModel.objects.get(id=each_allocation['id'])
                    try:
                        notify_persons = []
                        if  current_allocation.NotifyTo is not None:     
                            notify_persons =[current_allocation.NotifyTo[each_person_no]['Name'] for each_person_no in range(len(current_allocation.NotifyTo))]
                            notify_emails = [current_allocation.NotifyTo[each_person_no]['Email'] for each_person_no in range(len(current_allocation.NotifyTo))]
                        else:
                            notify_emails = ""
                            notify_persons = []
                    except Exception as e:
                        print(e)
                    # print("number of benches",current_allocation.NumberOfbenches)
                    # print("allocated to",current_allocation.AllocatedTo)
                    # print("enumber of benches",current_allocation.NumberOfbenches)
                    # print("eallocated to",current_allocation.AllocatedTo)
                    # print("ebenchdata",current_allocation.BenchData)
                    # print("eduration",current_allocation.Duration)
                    message = "This email is a Remainder of your allocated Lab Benches is <b>about to Expire next week</b>"
                    subject = "Bench request is about to expire for "
                    mail_data = {
                                    "User":current_allocation.AllocatedTo[0]['Name'],
                                    "WWID":current_allocation.AllocatedTo[0]['WWID'],
                                    "program":current_allocation.Program,
                                    "sku":current_allocation.Sku,
                                    "lab_name":current_allocation.Location.Name,
                                    "vendor":current_allocation.Vendor,
                                    "allocatedto":current_allocation.AllocatedTo[0]['Name'],
                                    "notifyto":','.join(notify_persons),
                                    "fromww":str(current_allocation.FromWW),
                                    "toww":str(current_allocation.ToWW),
                                    "duration":current_allocation.Duration,
                                    "remarks":current_allocation.Remarks,
                                    "function":current_allocation.Function,
                                    "team":current_allocation.Team,
                                    "id":current_allocation.id,
                                    "numberofbenches":current_allocation.NumberOfbenches,
                                    "message":message,
                                    "subject":subject,
                                    "department":current_allocation.Department,
                                    "function":current_allocation.Function
                                }
                    bench_data = []
                    rack_shelf_data = []
                    print(f"Bench_data: {current_allocation.BenchData}. PID: {os.getpid()}")
                    schedular_logger.info(f"Bench_data: {current_allocation.BenchData}. PID: {os.getpid()}")
                    if "BenchData" in current_allocation.__dict__ and current_allocation.BenchData:
                        for each_bench in current_allocation.BenchData:
                            if 'Rack' in each_bench:
                                rack_shelf_data.append(each_bench)
                            else:
                                bench_data.append(each_bench)
                    mail_data["bench_data"] = bench_data
                    mail_data["Rack-Shelf"] = rack_shelf_data
                    TO.append(' '+str(current_allocation.AllocatedTo[0]['Email']))
                    if notify_emails:
                        Cc = notify_emails
                    else:
                        Cc = []
                    Cc=Cc+CC
                    mail = ExpiryEmail(FROM,TO,Cc,mail_data)
                    mail.sendmail()
                    TO.pop()
                    schedular_logger.info(f"Bench Expiry email sent for id {current_allocation.id}, \
                    User {current_allocation.AllocatedTo[0]['Name']} for benches {current_allocation.BenchData}")


                    # new mail implementation

                


        schedular_logger.info("Scheduler Completed Execution")
        print("Scheduler Completed Execution")
    except Exception as e:
        print(e)


async def fetch_data(session, url, payload):
    try:
        async with session.post(url, json=payload) as response:
            response.raise_for_status()
            data = await response.json()
            return data, payload['team']
    except aiohttp.ClientError as e:
        return {"status": "An error occurred.", "error": str(e)}, payload['team']
    except json.JSONDecodeError as e:
        return {"status": "Invalid JSON response.", "error": str(e)}, payload['team']

async def process_payloads(payloads):
    url = "https://labspaceapi.apps1-bg-int.icloud.intel.com/home/GetDrillDownChartData/"
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_data(session, url, payload) for payload in payloads]
        return await asyncio.gather(*tasks)

def analyze_data(data, team):
    FROM = 'LabSpaceManager@intel.com'   
    CC = []
    TO = ['sakthirajanx.sembulingam@intel.com']
    if not isinstance(data, list):
        return {"status": f"Invalid data format for team {team}.", "data": data}
    
    all_data = next((item for item in data if item.get('category') == 'All'), None)
    if not all_data:
        return {"status": f"Category 'All' not found in API data for team {team}."}

    all_value = all_data.get('value')
    all_report = all_data.get('Report', [{}])[0]
    allocated_data = all_report.get('Allocated', [])
    free_report = all_report.get('Free', [])

    bench_data_length = sum(len(allocation.get('BenchData', [])) for allocation in allocated_data)
    free_report_count = sum(
        len(label_list)
        for free_report_entry in free_report
        for labels_list in free_report_entry.values()
        for labels in labels_list
        for label_list in labels.values()
    )

    total = bench_data_length + free_report_count
    message = f"This email is a confirmation of count for {team} matching in home page or not"
    subject = f"Confirmation of Home Page count for {team}"
    mail_data = {
        "team": team,
        "bench_data_length": bench_data_length,
        "free_report_count": free_report_count,
        "total": total,
        "all_value": all_value,
        "match": all_value == total,
        "message": message,
        "subject": subject,
    }
    # Send an email with the result
    mail = CountConfirmation(FROM, TO, CC, mail_data)
    mail.sendmail()

    return {
        "team": team,
        "bench_data_length": bench_data_length,
        "free_report_count": free_report_count,
        "total": total,
        "all_value": all_value,
        "match": all_value == total
    }


def CheckCounntSchedular():
    """ Method to be called by scheduler """
    try:
        initial_payloads = [{"team": "CCG"}, {"team": "PSE"}, {"team": "SIV"}, {"team": "CLSS"}, {"team": "C4S"}]
        # for payload in initial_payloads:
        #     print("payload",payload)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(process_payloads(initial_payloads))

        result_data = {team: analyze_data(data, team) for data, team in results}

        with open('results.json', 'w') as f:
            json.dump(result_data, f, indent=4)

        print({"status": "Data processed successfully.", "results": result_data})
    except Exception as e:
        print(traceback.format_exc())
        print({"status": "An error occurred.", "error": str(e)})