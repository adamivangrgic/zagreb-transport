from google.transit import gtfs_realtime_pb2
import requests, time


while True:
    with open("feed.txt", "a") as f:
        feed = gtfs_realtime_pb2.FeedMessage()
        response = requests.get("https://zet.hr/gtfs-rt-protobuf")
        feed.ParseFromString(response.content)
        
        f.write(str(feed))
        
    time.sleep(20)
