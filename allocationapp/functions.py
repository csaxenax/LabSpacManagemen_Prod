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
import calendar
from django.db.models import Q
from .models import AllocationDetailsModel,LabModel,UserModel
from .mail import Email,ExpiryEmail

import logging
logger = logging.getLogger(__name__)
schedular_logger = logging.getLogger('scheduler_logger')


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
        allocation_data = AllocationDetailsModel.objects.filter(status='allocated').values('id','Program','Sku','Vendor','FromWW',
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
                if (each_allocation['ToWW'] == current_workweek) or \
                    (each_allocation['ToWW'] == previous_workweek_1) or \
                        (each_allocation['ToWW'] == previous_workweek) or \
                            (int(each_allocation['ToWW'][2:]) < int(year)) or \
                                ((int(each_allocation['ToWW'][2:]) == int(year)) and (int(each_allocation['ToWW'][:2]) < int(current_workweek[:2]))):
                    
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
                    for each_bench_request in benchdata:
                        for each_bench_row in lab_query.BenchDetails:
                            for each_bench_column_no in range(len(each_bench_row['seats'])):
                                if each_bench_row['seats'][each_bench_column_no]['labelNo'] == each_bench_request:
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
                                "id":current_allocation.id,
                                "numberofbenches":current_allocation.NumberOfbenches,
                                "bench_data":current_allocation.BenchData,
                                "message":message,
                                "subject":subject,
                                "deallocatedby":current_allocation.DeallocatedBy,
                            }
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
                                "team":current_allocation.Team,
                                "id":current_allocation.id,
                                "numberofbenches":current_allocation.NumberOfbenches,
                                "bench_data":current_allocation.BenchData,
                                "message":message,
                                "subject":subject,
                            }
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
