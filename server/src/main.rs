use actix_cors::Cors;
use actix_web::get;
use actix_web::post;
use actix_web::web;
use actix_web::App;
use actix_web::HttpResponse;
use actix_web::HttpServer;
use actix_web::Responder;
use chrono::DateTime;
use chrono::Local;
use once_cell::sync::OnceCell;
use prettytable::row;
use prettytable::Table;
use redis::Client;
use redis::Commands;
use redis::Connection;
use serde::Deserialize;
use serde::Serialize;
use std::collections::BTreeMap;
use std::collections::HashMap;

/* JSON
{
    "password": "123456",
    "gpu": ["null"],
    "hostname": "homelab",
    "net": {"docker0": "172.17.0.1", "lo": "127.0.0.1", "vethbace035": "fe80::9caf:e9ff:fe7d:e1c8", "enp38s0": "null", "eno1": "192.168.1.33"},
    "mem": {"used": "2.4 GB", "total": "67.4 GB"},
    "swap": {"total": "1024.5 MB", "used": "0 B"},
    "cpu": {"idle": 1.0, "user": 1.4753625e-10, "nice": 0.0, "temp": 40.85, "interrupt": 0.0, "system": 0.0},
    "other": {"uptime": "0 day 6 hour 1 minutes 55 sec", "nowtime": "2023-04-26 16:06:05"}
}
*/

static RD_CONNECTION: OnceCell<Client> = OnceCell::new();

#[derive(Deserialize, Serialize, Clone, Debug)]
struct SingleCardDetail {
    name: String,
    driver_version: String,
    temperature_gpu: String,
    utilization_gpu: String,
    utilization_memory: String,
    memory_total: String,
    memory_free: String,
    memory_used: String,
}

#[derive(Deserialize, Serialize, Clone)]
struct ServerCardsInfo {
    details: Vec<SingleCardDetail>,
    users: Vec<String>,
}

#[derive(Deserialize, Serialize, Clone)]
struct ServerInfo {
    password: String,
    gpu: ServerCardsInfo,
    hostname: String,
    net: HashMap<String, String>,
    mem: HashMap<String, String>,
    swap: HashMap<String, String>,
    cpu: HashMap<String, f32>,
    other: HashMap<String, String>,
}

const PASSWORD: &str = "123456";

#[get("/")]
async fn hello() -> impl Responder {
    HttpResponse::Ok().body("Hello World")
}

#[get("/ping")]
async fn ping() -> impl Responder {
    HttpResponse::Ok().body("pong")
}

fn redis_connection() -> Connection {
    let client = RD_CONNECTION.get().unwrap();
    let con = match client.get_connection() {
        Ok(c) => c,
        Err(e) => panic!("Get redis connection failed: {}", e),
    };
    con
}

fn redis_database() -> BTreeMap<String, ServerInfo> {
    let mut con = redis_connection();
    let keys: Vec<String> = match con.keys("*") {
        Ok(r) => r,
        Err(e) => panic!("get all keys failed: {}", e),
    };
    // let mut database: HashMap<String, ServerInfo> = HashMap::new();
    let mut database: BTreeMap<String, ServerInfo> = BTreeMap::new();
    for k in keys {
        let v: String = con.get(&k).unwrap();
        let v: ServerInfo = serde_json::from_str(&v).unwrap();
        database.insert(k, v);
    }
    database
}

#[post("/update")]
async fn update(server_info: web::Json<ServerInfo>) -> impl Responder {
    let mut con = redis_connection();
    // println!("Get: {}", gpu_info.hostname);
    if server_info.password != PASSWORD {
        HttpResponse::Ok().body(format!("password wrong!"))
    } else {
        let server_time: DateTime<Local> = Local::now();
        let server_time_str = server_time.format("%H:%M:%S").to_string();
        let mut server_info_clone = server_info.clone();
        server_info_clone
            .other
            .insert("new_nowtime".to_string(), server_time_str);

        let hostname = &server_info_clone.hostname;
        let serde_server_info = match serde_json::to_string(&server_info_clone) {
            Ok(s) => s,
            Err(e) => panic!("Convert struct to string failed: {}", e),
        };
        let _: () = con
            .set_ex(hostname, serde_server_info, 60)
            .expect("Redis set failed");

        HttpResponse::Ok().body(format!("Welcome {}!", hostname))
    }
}

fn database_process(database: BTreeMap<String, ServerInfo>) -> BTreeMap<String, ServerInfo> {
    let mut hm = BTreeMap::new();
    for (name, mut server_info) in database {
        let gpu_users = &server_info.gpu.users;
        let mut new_gpu_users = Vec::new();
        for gpu_user in gpu_users {
            // example: "/public/test"
            if gpu_user.contains("/") {
                let tmp_vec: Vec<&str> = gpu_user.split("/").collect();
                if tmp_vec.len() > 2 {
                    let new_gpu = tmp_vec[2]; // change here
                    new_gpu_users.push(new_gpu.to_string());
                } else {
                    new_gpu_users.push(tmp_vec[tmp_vec.len() - 1].to_string());
                }
            } else if gpu_user.contains("no running processes found") {
                new_gpu_users.push("null".to_string());
            } else if gpu_user.contains("driver failed") {
                new_gpu_users.push("driver failed".to_string());
            } else {
                // new_gpu_vec.push("".to_string());
                new_gpu_users.push(gpu_user.to_string());
            }
        }
        server_info.gpu.users = new_gpu_users;
        hm.insert(name, server_info);
    }
    hm
}

#[get("/info")]
async fn info() -> impl Responder {
    let database = redis_database();

    let name_title = "name";
    let ip_title = "addr";
    let cpu_system_title = "cpu@s";
    let cpu_user_title = "cpu@u";
    let cpu_temp_title = "cpu@t";
    let gpu_name_title = "gpu device";
    let gpu_util_title = "gpu@u";
    let gpu_memory_title = "gpu@m";
    let gpu_temp_title = "gpu@t";
    let gpu_user_title = "gpu user";
    let heartbeat_title = "heartbeat";

    let mut table = Table::new();
    table.add_row(row![
        c -> name_title,
        c -> ip_title,
        c -> cpu_system_title,
        c -> cpu_user_title,
        c -> cpu_temp_title,
        c -> gpu_name_title,
        c -> gpu_util_title,
        c -> gpu_memory_title,
        c -> gpu_temp_title,
        c -> gpu_user_title,
        c -> heartbeat_title
    ]);

    let new_database = database_process(database);
    for (hostname, server_info) in new_database {
        if hostname.len() > 0 {
            let mut ip_info = String::new();
            let new_net: BTreeMap<String, String> = server_info.net.into_iter().collect();
            for (interface_name, ip) in new_net {
                if !ip.contains("null") && !ip.contains("127.0.0.1") {
                    ip_info += &format!("{}: {}\n", interface_name, ip);
                }
            }
            let ip_info = ip_info.trim();

            let cpu_system = match server_info.cpu.get("system") {
                Some(c) => format!("{:.0} %", c * 100.0),
                None => String::from("0"),
            };
            let cpu_user = match server_info.cpu.get("user") {
                Some(c) => format!("{:.0} %", c * 100.0),
                None => String::from("0"),
            };
            let cpu_temp = match server_info.cpu.get("temp") {
                Some(t) => format!("{:.0} C", t),
                None => format!("{:.0} C", 0.0),
            };

            let gpu_device = server_info.gpu.details;
            let gpu_users = server_info.gpu.users;
            let mut gpu_name = String::new();
            let mut gpu_util = String::new();
            let mut gpu_memory = String::new();
            let mut gpu_temp = String::new();
            for gd in gpu_device {
                gpu_name += &format!("{} ({})\n", gd.name, gd.driver_version);
                gpu_util += &format!("{}\n", gd.utilization_gpu);
                gpu_memory += &format!("{}/{}\n", gd.memory_used, gd.memory_total);
                gpu_temp += &format!("{} C\n", gd.temperature_gpu);
            }
            let gpu_name = gpu_name.trim();
            let gpu_util = gpu_util.trim();
            let gpu_memory = gpu_memory.trim();
            let gpu_temp = gpu_temp.trim();

            let mut gpu_user = String::new();
            for gu in gpu_users {
                gpu_user += &format!("{}\n", gu);
            }
            let gpu_user = gpu_user.trim();

            let heartbeat_time = match server_info.other.get("new_nowtime") {
                Some(u) => u.to_string(),
                None => {
                    let server_time_str = Local::now().format("%H:%M:%S").to_string();
                    server_time_str
                }
            };

            table.add_row(row![
                c -> hostname,
                c -> ip_info,
                c -> cpu_system,
                c -> cpu_user,
                c -> cpu_temp,
                c -> gpu_name,
                c -> gpu_util,
                c -> gpu_memory,
                c -> gpu_temp,
                c -> gpu_user,
                c -> heartbeat_time
            ]);
        }
    }

    let date_as_string = Local::now().format("%Y-%m-%d %H:%M:%S");
    let info_str = format!(">> {} [AI Sec Lab]", date_as_string);
    // let powered = "Powered by Rust\n";
    let version = option_env!("CARGO_PKG_VERSION").unwrap();
    let powered = format!(">> Powered by Jay (v{})", version);

    let mut note = String::from(">> cpu@s: cpu system space utilization\n");
    note += ">> cpu@u: cpu user space utilization\n";
    note += ">> cpu@t: cpu temperature\n";
    note += ">> gpu@u: gpu utilization\n";
    note += ">> gpu@m: gpu memory\n";
    note += ">> gpu@t: gpu temperature";

    let lines = format!("{}\n{}{}\n{}", info_str, table.to_string(), note, powered);

    HttpResponse::Ok().body(lines)
}

#[get("/info2")]
async fn info2() -> impl Responder {
    let database = redis_database();
    HttpResponse::Ok().json(database)
}

#[cfg(test)]
mod tests {
    use chrono::Local;
    use itertools::Itertools;
    use std::collections::HashMap;
    #[test]
    fn test_hashmap() {
        let mut hashmap = HashMap::new();
        hashmap.insert("a", 1);
        hashmap.insert("b", 2);
        hashmap.insert("c", 3);
        for (k, v) in hashmap.iter().sorted_by_key(|x| x.0) {
            println!("{:?}: {:?}", k, v);
        }
        let keys = hashmap.keys();
        println!("{:?}", keys);
        let mut keys_vec = Vec::new();
        for k in keys {
            keys_vec.push(k.to_string());
        }
        println!("{:?}", keys_vec);
        for x in 0..10 {
            println!("{}", x);
        }
        let x = "123";
        let x_len = 10;
        for o in 0..((x_len - x.len()) / 2) {
            println!("o: {}", o);
        }
        let date_as_string = Local::now().format("%Y-%m-%d %H:%M:%S");
        println!("{}", date_as_string);
        assert_eq!(10, 10);
    }
    #[test]
    fn test_split() {
        let path = "/public/test";
        let path_split: Vec<&str> = path.split("/").collect();
        println!("{:?}", path_split);
    }
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    println!("Web is running...");
    // let pool = PgPool::connect(PG_DATABASE_URL)
    //     .await
    //     .expect("Connect to postgre failed");
    // PG_CONNECTION.set(pool).expect("Set PG_CONNECTION failed");

    let client = match redis::Client::open("redis://127.0.0.1/") {
        Ok(c) => c,
        Err(e) => panic!("Connect to redis failed: {}", e),
    };
    RD_CONNECTION.set(client).expect("Set RD_CONNECTION failed");

    HttpServer::new(|| {
        let cors = Cors::default().allow_any_origin().send_wildcard();
        App::new()
            .wrap(cors)
            .service(hello)
            .service(ping)
            .service(update)
            .service(info)
            .service(info2)
    })
    .bind(("0.0.0.0", 7070))?
    .run()
    .await
}
